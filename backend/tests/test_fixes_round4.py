"""Tests for round-4 fixes: draft posts and hide_follows toggle."""
import os
import time
import pytest
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

BASE = os.environ.get("REACT_APP_BACKEND_URL")
if not BASE:
    fe = Path(__file__).resolve().parents[2] / "frontend" / ".env"
    for line in fe.read_text().splitlines():
        if line.startswith("REACT_APP_BACKEND_URL="):
            BASE = line.split("=", 1)[1].strip()
            break
API = BASE.rstrip("/") + "/api"

TEACHER = {"email": "teacher@teachhub.com", "password": "teacher12345"}


def h(t):
    return {"Authorization": f"Bearer {t}"}


@pytest.fixture(scope="module")
def teacher_token():
    r = requests.post(f"{API}/auth/login", json=TEACHER)
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture(scope="module")
def other_user():
    email = f"test_r4_{int(time.time())}@example.com"
    r = requests.post(f"{API}/auth/register",
                      json={"email": email, "password": "abcd1234", "name": "TEST_R4"})
    assert r.status_code == 200, r.text
    tok = r.json()["token"]
    uid = r.json()["user"]["id"]
    yield {"token": tok, "id": uid}
    requests.delete(f"{API}/users/me", headers=h(tok))


# ---------- Drafts (FIX7) ----------
class TestDraftPosts:
    def test_draft_hidden_from_public_feed(self, teacher_token):
        payload = {"type": "html", "title": "TEST_draft_hidden", "subject": "physics",
                   "grade": "7-8", "html_code": "<b>d</b>", "is_draft": True}
        r = requests.post(f"{API}/tasks", json=payload, headers=h(teacher_token))
        assert r.status_code == 200, r.text
        tid = r.json()["id"]
        assert r.json().get("is_draft") is True
        try:
            # Public feed excludes drafts
            lst = requests.get(f"{API}/tasks", params={"search": "TEST_draft_hidden"}).json()
            assert all(it["id"] != tid for it in lst["items"])
            # Guest GET returns 404
            g = requests.get(f"{API}/tasks/{tid}")
            assert g.status_code == 404
        finally:
            requests.delete(f"{API}/tasks/{tid}", headers=h(teacher_token))

    def test_draft_visible_to_owner(self, teacher_token):
        payload = {"type": "html", "title": "TEST_draft_owner", "subject": "physics",
                   "grade": "7-8", "html_code": "<b>d</b>", "is_draft": True}
        r = requests.post(f"{API}/tasks", json=payload, headers=h(teacher_token)).json()
        tid = r["id"]
        try:
            # Owner can GET the task
            g = requests.get(f"{API}/tasks/{tid}", headers=h(teacher_token))
            assert g.status_code == 200
            assert g.json()["is_draft"] is True
            # Owner sees it in /users/me/tasks
            mine = requests.get(f"{API}/users/me/tasks", headers=h(teacher_token)).json()
            assert any(t["id"] == tid for t in mine)
        finally:
            requests.delete(f"{API}/tasks/{tid}", headers=h(teacher_token))

    def test_draft_hidden_from_other_user(self, teacher_token, other_user):
        payload = {"type": "html", "title": "TEST_draft_other", "subject": "physics",
                   "grade": "7-8", "html_code": "<b>d</b>", "is_draft": True}
        r = requests.post(f"{API}/tasks", json=payload, headers=h(teacher_token)).json()
        tid = r["id"]
        try:
            # Other authenticated user cannot view the draft
            g = requests.get(f"{API}/tasks/{tid}", headers=h(other_user["token"]))
            assert g.status_code == 404
        finally:
            requests.delete(f"{API}/tasks/{tid}", headers=h(teacher_token))

    def test_draft_toggle_off_publishes(self, teacher_token):
        payload = {"type": "html", "title": "TEST_draft_toggle", "subject": "physics",
                   "grade": "7-8", "html_code": "<b>d</b>", "is_draft": True}
        tid = requests.post(f"{API}/tasks", json=payload, headers=h(teacher_token)).json()["id"]
        try:
            # Update to publish (is_draft=False)
            upd = {"type": "html", "title": "TEST_draft_toggle", "subject": "physics",
                   "grade": "7-8", "html_code": "<b>d</b>", "is_draft": False}
            u = requests.put(f"{API}/tasks/{tid}", json=upd, headers=h(teacher_token))
            assert u.status_code == 200
            assert u.json()["is_draft"] is False
            # Guest can now view
            g = requests.get(f"{API}/tasks/{tid}")
            assert g.status_code == 200
        finally:
            requests.delete(f"{API}/tasks/{tid}", headers=h(teacher_token))

    def test_draft_excluded_from_following_feed(self, teacher_token, other_user):
        me = requests.get(f"{API}/auth/me", headers=h(teacher_token)).json()
        # other follows teacher
        requests.post(f"{API}/users/{me['id']}/follow", headers=h(other_user["token"]))
        payload = {"type": "html", "title": "TEST_draft_ff", "subject": "physics",
                   "grade": "7-8", "html_code": "<b>d</b>", "is_draft": True}
        tid = requests.post(f"{API}/tasks", json=payload, headers=h(teacher_token)).json()["id"]
        try:
            f = requests.get(f"{API}/feed/following", headers=h(other_user["token"])).json()
            assert all(it["id"] != tid for it in f["items"])
        finally:
            requests.delete(f"{API}/tasks/{tid}", headers=h(teacher_token))
            requests.post(f"{API}/users/{me['id']}/follow", headers=h(other_user["token"]))  # unfollow


# ---------- Hide follows (FIX6) ----------
class TestHideFollows:
    def test_hide_follows_toggle(self, teacher_token, other_user):
        me = requests.get(f"{API}/auth/me", headers=h(teacher_token)).json()
        teacher_id = me["id"]
        # Ensure other follows teacher so counts>0
        requests.post(f"{API}/users/{teacher_id}/follow", headers=h(other_user["token"]))
        try:
            # Turn ON hide_follows on teacher's account
            u = requests.put(f"{API}/users/me", json={"hide_follows": True}, headers=h(teacher_token))
            assert u.status_code == 200
            assert u.json().get("hide_follows") is True

            # Other user sees profile without followers/following counts
            prof = requests.get(f"{API}/users/{teacher_id}", headers=h(other_user["token"])).json()
            assert prof.get("hide_follows") is True
            # counts hidden -> either 0 or None
            assert not prof.get("followers_count")
            assert not prof.get("following_count")

            # followers/following endpoints should not leak lists
            fl = requests.get(f"{API}/users/{teacher_id}/followers",
                              headers=h(other_user["token"])).json()
            assert fl == [] or fl is None or (isinstance(fl, list) and len(fl) == 0)

            fg = requests.get(f"{API}/users/{teacher_id}/following",
                              headers=h(other_user["token"])).json()
            assert fg == [] or fg is None or (isinstance(fg, list) and len(fg) == 0)

            # Owner still sees own counts
            self_prof = requests.get(f"{API}/users/{teacher_id}", headers=h(teacher_token)).json()
            assert self_prof.get("followers_count", 0) >= 1
        finally:
            # Restore
            requests.put(f"{API}/users/me", json={"hide_follows": False}, headers=h(teacher_token))
            requests.post(f"{API}/users/{teacher_id}/follow", headers=h(other_user["token"]))  # unfollow
