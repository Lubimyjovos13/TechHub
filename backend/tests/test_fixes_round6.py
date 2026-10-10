"""Tests for round 6 fixes: welcome draft on register & privacy-preview backend behavior."""
import os, time, uuid, requests, pytest
from dotenv import load_dotenv
load_dotenv("/app/frontend/.env")

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"

TEACHER = {"email": "teacher@teachhub.com", "password": "teacher12345"}


def _auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


def _register():
    email = f"TEST_wc_{uuid.uuid4().hex[:10]}@example.com"
    r = requests.post(f"{API}/auth/register", json={
        "email": email, "password": "Password12345", "name": "TEST User"
    })
    assert r.status_code == 200, r.text
    d = r.json()
    return d["token"], d["user"], email


def _login(creds):
    r = requests.post(f"{API}/auth/login", json=creds)
    assert r.status_code == 200, r.text
    return r.json()["token"], r.json()["user"]


# -------- FIX2 welcome draft --------
class TestWelcomeDraft:
    def test_register_creates_one_welcome_draft(self):
        token, user, _ = _register()
        uid = user["id"]
        # my posts (auth) should include the welcome draft
        r = requests.get(f"{API}/users/me/tasks", headers=_auth_headers(token))
        assert r.status_code == 200
        mine = r.json().get("items", r.json()) if isinstance(r.json(), dict) else r.json()
        # response might be list or dict; normalize
        items = mine if isinstance(mine, list) else mine.get("items", [])
        welcomes = [t for t in items if t.get("title", "").startswith("👋 Welcome to TeachHub")]
        assert len(welcomes) == 1, f"expected 1 welcome draft, got {len(welcomes)}"
        w = welcomes[0]
        assert w.get("is_draft") is True
        assert w.get("type") == "blog"
        # Open by id as author
        r2 = requests.get(f"{API}/tasks/{w['id']}", headers=_auth_headers(token))
        assert r2.status_code == 200
        body = r2.json()
        assert "Welcome" in body.get("title", "")
        assert "HTML" in (body.get("body") or "") or "worksheet" in (body.get("body") or "").lower()

    def test_welcome_is_private_from_public_feed(self):
        token, user, _ = _register()
        # Public feed search
        r = requests.get(f"{API}/tasks", params={"search": "Welcome to TeachHub"})
        assert r.status_code == 200
        data = r.json()
        total = data.get("total", len(data.get("items", [])))
        # Nothing with our welcome title should appear from public feed
        items = data.get("items", [])
        assert not any(t.get("title", "").startswith("👋 Welcome") for t in items), items

    def test_welcome_absent_from_public_user_tasks(self):
        token, user, _ = _register()
        r = requests.get(f"{API}/users/{user['id']}/tasks")
        assert r.status_code == 200
        data = r.json()
        items = data.get("items", data if isinstance(data, list) else [])
        assert not any(t.get("title", "").startswith("👋 Welcome") for t in items)

    def test_welcome_404_for_guest(self):
        token, user, _ = _register()
        # find id
        r = requests.get(f"{API}/users/me/tasks", headers=_auth_headers(token))
        d = r.json()
        items = d if isinstance(d, list) else d.get("items", [])
        wid = [t for t in items if t.get("title", "").startswith("👋 Welcome")][0]["id"]
        # guest
        r2 = requests.get(f"{API}/tasks/{wid}")
        assert r2.status_code == 404
        # other user
        t2, _, _ = _register()
        r3 = requests.get(f"{API}/tasks/{wid}", headers=_auth_headers(t2))
        assert r3.status_code == 404
        # author can open
        r4 = requests.get(f"{API}/tasks/{wid}", headers=_auth_headers(token))
        assert r4.status_code == 200


# -------- FIX1 privacy backend behavior --------
class TestPrivacyHideFlags:
    @pytest.fixture(scope="class")
    def teacher_ctx(self):
        token, u = _login(TEACHER)
        yield token, u
        # restore
        requests.put(f"{API}/users/me", json={"hide_followers": False, "hide_following": False},
                     headers=_auth_headers(token))

    def test_hide_followers_hides_from_others(self, teacher_ctx):
        token, u = teacher_ctx
        uid = u["id"]
        # enable hide_followers
        r = requests.put(f"{API}/users/me", json={"hide_followers": True, "hide_following": False},
                         headers=_auth_headers(token))
        assert r.status_code == 200
        # other user's view
        t2, _, _ = _register()
        r2 = requests.get(f"{API}/users/{uid}", headers=_auth_headers(t2))
        assert r2.status_code == 200
        d = r2.json()
        assert d.get("hide_followers") is True
        assert d.get("followers_count") in (0, None)
        # followers endpoint should be blocked / empty
        rf = requests.get(f"{API}/users/{uid}/followers", headers=_auth_headers(t2))
        # either 403 or empty list
        if rf.status_code == 200:
            data = rf.json()
            items = data if isinstance(data, list) else data.get("items", [])
            assert items == []
        else:
            assert rf.status_code in (403, 404)
        # following endpoint should still work for the "other viewer"
        rg = requests.get(f"{API}/users/{uid}/following", headers=_auth_headers(t2))
        assert rg.status_code == 200

    def test_hide_following_hides_from_others(self, teacher_ctx):
        token, u = teacher_ctx
        uid = u["id"]
        r = requests.put(f"{API}/users/me", json={"hide_followers": False, "hide_following": True},
                         headers=_auth_headers(token))
        assert r.status_code == 200
        t2, _, _ = _register()
        rg = requests.get(f"{API}/users/{uid}/following", headers=_auth_headers(t2))
        if rg.status_code == 200:
            data = rg.json()
            items = data if isinstance(data, list) else data.get("items", [])
            assert items == []
        else:
            assert rg.status_code in (403, 404)
        rf = requests.get(f"{API}/users/{uid}/followers", headers=_auth_headers(t2))
        assert rf.status_code == 200

    def test_self_still_sees_own_lists(self, teacher_ctx):
        token, u = teacher_ctx
        uid = u["id"]
        requests.put(f"{API}/users/me", json={"hide_followers": True, "hide_following": True},
                     headers=_auth_headers(token))
        rf = requests.get(f"{API}/users/{uid}/followers", headers=_auth_headers(token))
        assert rf.status_code == 200
        rg = requests.get(f"{API}/users/{uid}/following", headers=_auth_headers(token))
        assert rg.status_code == 200


# ---------- Light regression ----------
class TestRegression:
    def test_login_teacher(self):
        t, u = _login(TEACHER)
        assert u["email"] == TEACHER["email"]

    def test_public_feed(self):
        r = requests.get(f"{API}/tasks", params={"limit": 5})
        assert r.status_code == 200
        d = r.json()
        assert "items" in d or isinstance(d, list)

    def test_publish_and_delete_blog(self):
        t, u = _login(TEACHER)
        payload = {"type": "blog", "title": "TEST_reg_blog", "subject": "other",
                   "grade": "university", "description": "d", "body": "hello", "is_draft": False}
        r = requests.post(f"{API}/tasks", json=payload, headers=_auth_headers(t))
        assert r.status_code in (200, 201), r.text
        tid = r.json().get("id") or r.json().get("_id")
        assert tid
        # delete
        rd = requests.delete(f"{API}/tasks/{tid}", headers=_auth_headers(t))
        assert rd.status_code in (200, 204)
