"""Tests for TeachHub new features: post types, upload/files, folders, follows, following feed."""
import io
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
    """Register a throwaway user for follow tests."""
    email = f"test_other_{int(time.time())}@example.com"
    r = requests.post(f"{API}/auth/register",
                      json={"email": email, "password": "abcd1234", "name": "TEST_Other"})
    assert r.status_code == 200, r.text
    tok = r.json()["token"]
    uid = r.json()["user"]["id"]
    yield {"token": tok, "id": uid, "email": email}
    requests.delete(f"{API}/users/me", headers=h(tok))


# ---------- Tiny PNG helper ----------
PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xff\xff?\x00\x05\xfe\x02\xfeA\xa1{\x93\x00\x00\x00\x00IEND\xaeB`\x82"
)


# ---------- Upload / Files ----------
class TestUploadAndFiles:
    def test_upload_requires_auth(self):
        r = requests.post(f"{API}/upload", files={"file": ("t.png", PNG_BYTES, "image/png")})
        assert r.status_code == 401

    def test_upload_png_and_fetch(self, teacher_token):
        r = requests.post(f"{API}/upload", headers=h(teacher_token),
                          files={"file": ("test.png", PNG_BYTES, "image/png")})
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["is_image"] is True
        assert data["url"].startswith("/api/files/")
        fid = data["file_id"]
        g = requests.get(f"{API}/files/{fid}")
        assert g.status_code == 200
        assert g.content == PNG_BYTES
        # download flag
        g2 = requests.get(f"{API}/files/{fid}", params={"download": "true"})
        assert g2.status_code == 200
        assert "attachment" in g2.headers.get("Content-Disposition", "")

    def test_upload_bad_extension(self, teacher_token):
        r = requests.post(f"{API}/upload", headers=h(teacher_token),
                          files={"file": ("x.exe", b"MZ", "application/octet-stream")})
        assert r.status_code == 400


# ---------- Post types validation ----------
class TestPostTypes:
    def test_html_task(self, teacher_token):
        payload = {"type": "html", "title": "TEST_html", "subject": "physics",
                   "grade": "7-8", "html_code": "<h1>hi</h1>"}
        r = requests.post(f"{API}/tasks", json=payload, headers=h(teacher_token))
        assert r.status_code == 200, r.text
        d = r.json()
        assert d["type"] == "html" and d["html_code"] == "<h1>hi</h1>"
        requests.delete(f"{API}/tasks/{d['id']}", headers=h(teacher_token))

    def test_blog_task_requires_body(self, teacher_token):
        payload = {"type": "blog", "title": "TEST_b", "subject": "literature", "grade": "9-11"}
        r = requests.post(f"{API}/tasks", json=payload, headers=h(teacher_token))
        assert r.status_code == 400

    def test_blog_task_ok(self, teacher_token):
        payload = {"type": "blog", "title": "TEST_blog", "subject": "literature",
                   "grade": "9-11", "body": "My experience..."}
        r = requests.post(f"{API}/tasks", json=payload, headers=h(teacher_token))
        assert r.status_code == 200
        d = r.json()
        assert d["type"] == "blog" and d["body"] == "My experience..."
        requests.delete(f"{API}/tasks/{d['id']}", headers=h(teacher_token))

    def test_worksheet_requires_files(self, teacher_token):
        payload = {"type": "worksheet", "title": "TEST_w", "subject": "chemistry", "grade": "5-6"}
        r = requests.post(f"{API}/tasks", json=payload, headers=h(teacher_token))
        assert r.status_code == 400

    def test_worksheet_with_upload_flow(self, teacher_token):
        up = requests.post(f"{API}/upload", headers=h(teacher_token),
                           files={"file": ("ws.png", PNG_BYTES, "image/png")}).json()
        payload = {"type": "worksheet", "title": "TEST_ws", "subject": "chemistry",
                   "grade": "5-6", "files": [up]}
        r = requests.post(f"{API}/tasks", json=payload, headers=h(teacher_token))
        assert r.status_code == 200
        d = r.json()
        assert d["type"] == "worksheet" and len(d["files"]) == 1
        # Verify persisted
        g = requests.get(f"{API}/tasks/{d['id']}").json()
        assert g["files"][0]["file_id"] == up["file_id"]
        # Edit preserves type & files
        pu = requests.put(f"{API}/tasks/{d['id']}", headers=h(teacher_token),
                         json={"type": "worksheet", "title": "TEST_ws_upd",
                               "subject": "chemistry", "grade": "5-6", "files": [up]})
        assert pu.status_code == 200
        assert pu.json()["type"] == "worksheet"
        assert pu.json()["title"] == "TEST_ws_upd"
        requests.delete(f"{API}/tasks/{d['id']}", headers=h(teacher_token))

    def test_type_filter_in_feed(self, teacher_token):
        # ensure worksheet exists
        up = requests.post(f"{API}/upload", headers=h(teacher_token),
                           files={"file": ("f.png", PNG_BYTES, "image/png")}).json()
        c = requests.post(f"{API}/tasks", json={"type": "worksheet", "title": "TEST_wsflt",
                                                "subject": "chemistry", "grade": "5-6",
                                                "files": [up]},
                          headers=h(teacher_token)).json()
        try:
            r = requests.get(f"{API}/tasks", params={"type": "worksheet"})
            assert r.status_code == 200
            items = r.json()["items"]
            assert len(items) > 0
            for it in items:
                assert it["type"] == "worksheet"
        finally:
            requests.delete(f"{API}/tasks/{c['id']}", headers=h(teacher_token))


# ---------- Folders ----------
class TestFolders:
    def test_folder_crud(self, teacher_token):
        # list
        r = requests.get(f"{API}/folders", headers=h(teacher_token))
        assert r.status_code == 200
        # create
        c = requests.post(f"{API}/folders", json={"name": "TEST_Folder"}, headers=h(teacher_token))
        assert c.status_code == 200
        fid = c.json()["id"]
        assert c.json()["name"] == "TEST_Folder"
        # confirm present
        lst = requests.get(f"{API}/folders", headers=h(teacher_token)).json()
        assert any(f["id"] == fid for f in lst)
        # delete
        d = requests.delete(f"{API}/folders/{fid}", headers=h(teacher_token))
        assert d.status_code == 200
        lst2 = requests.get(f"{API}/folders", headers=h(teacher_token)).json()
        assert all(f["id"] != fid for f in lst2)

    def test_folders_require_auth(self):
        assert requests.get(f"{API}/folders").status_code == 401


# ---------- Follows / Profiles / Following feed ----------
class TestFollows:
    def test_public_profile_and_follow_toggle(self, other_user, teacher_token):
        # get teacher id via login response
        teacher_me = requests.get(f"{API}/auth/me", headers=h(teacher_token)).json()
        teacher_id = teacher_me["id"]

        prof = requests.get(f"{API}/users/{teacher_id}").json()
        assert prof["id"] == teacher_id
        assert "post_count" in prof and "followers_count" in prof and "following_count" in prof
        base_followers = prof["followers_count"]

        # other_user follows teacher
        r = requests.post(f"{API}/users/{teacher_id}/follow", headers=h(other_user["token"]))
        assert r.status_code == 200
        assert r.json()["following"] is True
        assert r.json()["followers_count"] == base_followers + 1

        # Idempotent unfollow
        r2 = requests.post(f"{API}/users/{teacher_id}/follow", headers=h(other_user["token"]))
        assert r2.json()["following"] is False
        assert r2.json()["followers_count"] == base_followers

    def test_cannot_follow_self(self, teacher_token):
        me = requests.get(f"{API}/auth/me", headers=h(teacher_token)).json()
        r = requests.post(f"{API}/users/{me['id']}/follow", headers=h(teacher_token))
        assert r.status_code == 400

    def test_followers_following_lists(self, other_user, teacher_token):
        me = requests.get(f"{API}/auth/me", headers=h(teacher_token)).json()
        teacher_id = me["id"]
        # follow
        requests.post(f"{API}/users/{teacher_id}/follow", headers=h(other_user["token"]))
        try:
            f = requests.get(f"{API}/users/{teacher_id}/followers").json()
            assert any(u["id"] == other_user["id"] for u in f)
            g = requests.get(f"{API}/users/{other_user['id']}/following").json()
            assert any(u["id"] == teacher_id for u in g)
        finally:
            requests.post(f"{API}/users/{teacher_id}/follow", headers=h(other_user["token"]))

    def test_following_feed(self, other_user, teacher_token):
        me = requests.get(f"{API}/auth/me", headers=h(teacher_token)).json()
        teacher_id = me["id"]
        # Empty state
        empty = requests.get(f"{API}/feed/following", headers=h(other_user["token"])).json()
        assert empty["total"] == 0
        # follow teacher -> feed should have items
        requests.post(f"{API}/users/{teacher_id}/follow", headers=h(other_user["token"]))
        try:
            f = requests.get(f"{API}/feed/following", headers=h(other_user["token"])).json()
            assert f["total"] >= 1
            for it in f["items"]:
                assert it["author_id"] == teacher_id
        finally:
            requests.post(f"{API}/users/{teacher_id}/follow", headers=h(other_user["token"]))

    def test_following_feed_requires_auth(self):
        assert requests.get(f"{API}/feed/following").status_code == 401
