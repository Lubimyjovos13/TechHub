"""TeachHub backend API tests (pytest)."""
import os
import time
import pytest
import requests
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/") if os.environ.get("REACT_APP_BACKEND_URL") else None
if not BASE_URL:
    # fall back to frontend/.env
    fe_env = Path(__file__).resolve().parents[2] / "frontend" / ".env"
    if fe_env.exists():
        for line in fe_env.read_text().splitlines():
            if line.startswith("REACT_APP_BACKEND_URL="):
                BASE_URL = line.split("=", 1)[1].strip().strip('"').rstrip("/")
                break

API = f"{BASE_URL}/api"

ADMIN = {"email": "admin@teachhub.com", "password": "admin12345"}
TEACHER = {"email": "teacher@teachhub.com", "password": "teacher12345"}


def _login(payload):
    r = requests.post(f"{API}/auth/login", json=payload, timeout=15)
    return r


@pytest.fixture(scope="session")
def teacher_token():
    r = _login(TEACHER)
    assert r.status_code == 200, r.text
    return r.json()["token"]


@pytest.fixture(scope="session")
def admin_token():
    r = _login(ADMIN)
    assert r.status_code == 200, r.text
    return r.json()["token"]


def h(token):
    return {"Authorization": f"Bearer {token}"}


# ---------------- Auth ----------------
class TestAuth:
    def test_login_teacher(self):
        r = _login(TEACHER)
        assert r.status_code == 200
        data = r.json()
        assert "token" in data and data["user"]["email"] == TEACHER["email"]
        assert data["user"]["role"] == "teacher"

    def test_login_admin(self):
        r = _login(ADMIN)
        assert r.status_code == 200
        assert r.json()["user"]["role"] == "admin"

    def test_login_bad(self):
        r = _login({"email": "teacher@teachhub.com", "password": "wrongpass"})
        assert r.status_code == 401

    def test_me_requires_auth(self):
        r = requests.get(f"{API}/auth/me")
        assert r.status_code == 401

    def test_me_ok(self, teacher_token):
        r = requests.get(f"{API}/auth/me", headers=h(teacher_token))
        assert r.status_code == 200
        assert r.json()["email"] == TEACHER["email"]

    def test_register_and_duplicate(self):
        email = f"test_user_{int(time.time())}@example.com"
        r = requests.post(f"{API}/auth/register", json={"email": email, "password": "abcd1234", "name": "TEST_User"})
        assert r.status_code == 200, r.text
        assert "token" in r.json()
        # duplicate
        r2 = requests.post(f"{API}/auth/register", json={"email": email, "password": "abcd1234", "name": "TEST_User"})
        assert r2.status_code == 400
        # cleanup by deleting via own account
        token = r.json()["token"]
        d = requests.delete(f"{API}/users/me", headers=h(token))
        assert d.status_code == 200

    def test_register_short_password(self):
        r = requests.post(f"{API}/auth/register",
                          json={"email": "x@x.com", "password": "short", "name": "X"})
        assert r.status_code == 422


# ---------------- Tasks list/get ----------------
class TestTasks:
    def test_list_default(self):
        r = requests.get(f"{API}/tasks")
        assert r.status_code == 200
        d = r.json()
        assert set(["items", "total", "page", "limit", "pages"]).issubset(d.keys())
        assert d["total"] >= 4
        # ensure html_code excluded from card, author_name present
        if d["items"]:
            assert "html_code" not in d["items"][0]
            assert "author_name" in d["items"][0]
            assert "_id" not in d["items"][0]

    def test_list_pagination(self):
        r = requests.get(f"{API}/tasks", params={"page": 1, "limit": 2})
        assert r.status_code == 200
        assert len(r.json()["items"]) <= 2

    def test_list_search(self):
        r = requests.get(f"{API}/tasks", params={"search": "z"})
        assert r.status_code == 200

    def test_list_filter_subject(self):
        r = requests.get(f"{API}/tasks", params={"subject": "mathematics"})
        assert r.status_code == 200
        for it in r.json()["items"]:
            assert it["subject"] == "mathematics"

    def test_list_filter_grade(self):
        r = requests.get(f"{API}/tasks", params={"grade": "5-6"})
        assert r.status_code == 200
        for it in r.json()["items"]:
            assert it["grade"] == "5-6"

    def test_get_task_and_view_increment(self):
        lst = requests.get(f"{API}/tasks").json()["items"]
        assert lst
        tid = lst[0]["id"]
        r1 = requests.get(f"{API}/tasks/{tid}")
        assert r1.status_code == 200
        v1 = r1.json()["views"]
        assert "html_code" in r1.json()
        r2 = requests.get(f"{API}/tasks/{tid}")
        assert r2.json()["views"] == v1 + 1

    def test_get_task_invalid(self):
        r = requests.get(f"{API}/tasks/deadbeef")
        assert r.status_code == 404


# ---------------- Task CRUD + likes/favs/report ----------------
class TestTaskCRUD:
    @pytest.fixture(scope="class")
    def created_task_id(self, teacher_token):
        payload = {
            "title": "TEST_Task",
            "subject": "mathematics",
            "grade": "5-6",
            "description": "desc",
            "html_code": "<h1>hi</h1>",
            "tags": ["algebra", "test"],
        }
        r = requests.post(f"{API}/tasks", json=payload, headers=h(teacher_token))
        assert r.status_code == 200, r.text
        tid = r.json()["id"]
        yield tid
        requests.delete(f"{API}/tasks/{tid}", headers=h(teacher_token))

    def test_create_persisted(self, created_task_id):
        r = requests.get(f"{API}/tasks/{created_task_id}")
        assert r.status_code == 200
        assert r.json()["title"] == "TEST_Task"

    def test_update(self, teacher_token, created_task_id):
        payload = {
            "title": "TEST_Task_updated",
            "subject": "physics",
            "grade": "7-8",
            "description": "new",
            "html_code": "<h2>upd</h2>",
            "tags": ["a"],
        }
        r = requests.put(f"{API}/tasks/{created_task_id}", json=payload, headers=h(teacher_token))
        assert r.status_code == 200
        # verify persisted
        g = requests.get(f"{API}/tasks/{created_task_id}").json()
        assert g["title"] == "TEST_Task_updated"
        assert g["subject"] == "physics"

    def test_unauthorized_edit(self, admin_token, created_task_id):
        # admin CAN edit (per code), so use a new user to check 403
        email = f"other_{int(time.time())}@x.com"
        r = requests.post(f"{API}/auth/register", json={"email": email, "password": "abcd1234", "name": "Other"})
        tok = r.json()["token"]
        try:
            payload = {"title": "bad", "subject": "mathematics", "grade": "5-6",
                       "description": "", "html_code": "<b/>", "tags": []}
            r2 = requests.put(f"{API}/tasks/{created_task_id}", json=payload, headers=h(tok))
            assert r2.status_code == 403
        finally:
            requests.delete(f"{API}/users/me", headers=h(tok))

    def test_like_toggle(self, teacher_token, created_task_id):
        r1 = requests.post(f"{API}/tasks/{created_task_id}/like", headers=h(teacher_token))
        assert r1.status_code == 200
        assert r1.json()["liked"] is True
        assert r1.json()["likes_count"] >= 1
        r2 = requests.post(f"{API}/tasks/{created_task_id}/like", headers=h(teacher_token))
        assert r2.json()["liked"] is False

    def test_favorite_toggle_and_list(self, teacher_token, created_task_id):
        r = requests.post(f"{API}/tasks/{created_task_id}/favorite", headers=h(teacher_token))
        assert r.status_code == 200
        assert r.json()["favorited"] is True
        favs = requests.get(f"{API}/users/me/favorites", headers=h(teacher_token))
        assert favs.status_code == 200
        assert any(t["id"] == created_task_id for t in favs.json())
        # untoggle
        r2 = requests.post(f"{API}/tasks/{created_task_id}/favorite", headers=h(teacher_token))
        assert r2.json()["favorited"] is False

    def test_report(self, teacher_token, created_task_id):
        r = requests.post(f"{API}/tasks/{created_task_id}/report",
                          json={"reason": "TEST spam"}, headers=h(teacher_token))
        assert r.status_code == 200

    def test_my_tasks(self, teacher_token, created_task_id):
        r = requests.get(f"{API}/users/me/tasks", headers=h(teacher_token))
        assert r.status_code == 200
        assert any(t["id"] == created_task_id for t in r.json())


# ---------------- User account ops ----------------
class TestUserAccount:
    def test_update_name_and_password(self):
        email = f"acct_{int(time.time())}@x.com"
        r = requests.post(f"{API}/auth/register",
                          json={"email": email, "password": "abcd1234", "name": "TEST_Init"})
        tok = r.json()["token"]
        try:
            u = requests.put(f"{API}/users/me", json={"name": "TEST_Renamed"}, headers=h(tok))
            assert u.status_code == 200
            assert u.json()["name"] == "TEST_Renamed"
            me = requests.get(f"{API}/auth/me", headers=h(tok)).json()
            assert me["name"] == "TEST_Renamed"

            pw = requests.put(f"{API}/users/me/password",
                              json={"current_password": "abcd1234", "new_password": "newpass123"}, headers=h(tok))
            assert pw.status_code == 200
            # login with new password
            l = _login({"email": email, "password": "newpass123"})
            assert l.status_code == 200
        finally:
            requests.delete(f"{API}/users/me", headers=h(tok))


# ---------------- Admin ----------------
class TestAdmin:
    def test_stats(self, admin_token):
        r = requests.get(f"{API}/admin/stats", headers=h(admin_token))
        assert r.status_code == 200
        for k in ("users", "tasks", "reports"):
            assert k in r.json()

    def test_users_list(self, admin_token):
        r = requests.get(f"{API}/admin/users", headers=h(admin_token))
        assert r.status_code == 200
        assert isinstance(r.json(), list) and len(r.json()) >= 2

    def test_reports_list(self, admin_token):
        r = requests.get(f"{API}/admin/reports", headers=h(admin_token))
        assert r.status_code == 200

    def test_non_admin_denied(self, teacher_token):
        r = requests.get(f"{API}/admin/stats", headers=h(teacher_token))
        assert r.status_code == 403

    def test_admin_cannot_delete_self(self, admin_token):
        me = requests.get(f"{API}/auth/me", headers=h(admin_token)).json()
        r = requests.delete(f"{API}/admin/users/{me['id']}", headers=h(admin_token))
        assert r.status_code == 400
