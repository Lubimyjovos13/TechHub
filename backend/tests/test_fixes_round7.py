"""Round 7 — tests for pin/highlight, Excel/DB export+import, admin users stats + promote,
error-reports (incl. guest), forgot/reset password token flow, comments, view count +=1."""
import os
import io
import json
import time
import pytest
import requests
from pymongo import MongoClient

BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "test_database")

ADMIN = {"email": "admin@teachhub.com", "password": "admin12345"}


def _login(email, password):
    r = requests.post(f"{API}/auth/login", json={"email": email, "password": password}, timeout=30)
    assert r.status_code == 200, r.text
    return r.json()["token"]


def _register(name="TEST R7"):
    stamp = int(time.time() * 1000)
    email = f"TEST_r7_{stamp}@example.com"
    r = requests.post(f"{API}/auth/register", json={"email": email, "password": "Password123!", "name": name}, timeout=30)
    assert r.status_code == 200, r.text
    data = r.json()
    return email, "Password123!", data["token"], data["user"]["id"]


def _auth(tok):
    return {"Authorization": f"Bearer {tok}"}


# ---------- Admin: Excel + DB export/import (merge, additive) ----------
def test_admin_export_excel():
    tok = _login(**ADMIN)
    r = requests.get(f"{API}/admin/export/excel", headers=_auth(tok), timeout=60)
    assert r.status_code == 200
    assert "spreadsheetml" in r.headers.get("content-type", "")
    assert r.content[:2] == b"PK"  # xlsx is zip


def test_admin_export_db_then_import_is_additive():
    tok = _login(**ADMIN)
    s_before = requests.get(f"{API}/admin/stats", headers=_auth(tok)).json()

    r = requests.get(f"{API}/admin/export/db", headers=_auth(tok), timeout=60)
    assert r.status_code == 200
    payload = r.json()
    assert "data" in payload and "users" in payload["data"]
    users_before = len(payload["data"]["users"])

    files = {"file": ("backup.json", json.dumps(payload).encode("utf-8"), "application/json")}
    r2 = requests.post(f"{API}/admin/import/db", headers=_auth(tok), files=files, timeout=120)
    assert r2.status_code == 200, r2.text
    j = r2.json()
    # Everything already in DB -> inserted counts should be 0 (additive, no duplicates)
    assert j["inserted"]["users"] == 0
    s_after = requests.get(f"{API}/admin/stats", headers=_auth(tok)).json()
    assert s_before == s_after, "Import must not change counts when re-importing own dump"
    assert users_before == s_after["users"]


# ---------- Admin: users stats + promote ----------
def test_admin_users_includes_stats_and_promote():
    atok = _login(**ADMIN)
    email, pw, utok, uid = _register("TEST R7 Promote")

    r = requests.get(f"{API}/admin/users", headers=_auth(atok), timeout=30)
    assert r.status_code == 200
    row = next((u for u in r.json() if u["id"] == uid), None)
    assert row is not None
    for k in ["folders_count", "drafts_count", "published_count", "time_spent_seconds", "created_at", "last_login_at"]:
        assert k in row

    # ping updates time_spent
    requests.post(f"{API}/users/me/ping", headers=_auth(utok))

    # promote
    r2 = requests.post(f"{API}/admin/users/{uid}/promote", headers=_auth(atok))
    assert r2.status_code == 200
    me = requests.get(f"{API}/auth/me", headers=_auth(utok)).json()
    assert me["role"] == "admin"


# ---------- Error reports: guest can post; admin lists + status updates ----------
def test_error_reports_guest_and_status_flow():
    r = requests.post(f"{API}/error-reports", json={"message": "TEST_r7 guest error", "url": "/x"}, timeout=30)
    assert r.status_code == 200

    atok = _login(**ADMIN)
    lst = requests.get(f"{API}/admin/error-reports", headers=_auth(atok)).json()
    rec = next((x for x in lst if x["message"] == "TEST_r7 guest error"), None)
    assert rec and rec["user_name"] == "Guest" and rec["status"] == "untouched"

    for st in ["in_progress", "fixed"]:
        p = requests.patch(f"{API}/admin/error-reports/{rec['id']}", headers=_auth(atok), json={"status": st})
        assert p.status_code == 200
    lst2 = requests.get(f"{API}/admin/error-reports", headers=_auth(atok)).json()
    assert next(x for x in lst2 if x["id"] == rec["id"])["status"] == "fixed"


# ---------- Forgot / reset password token flow (fetch token from Mongo) ----------
def test_forgot_reset_password_flow_single_use():
    email, pw, utok, uid = _register("TEST R7 Reset")
    r = requests.post(f"{API}/auth/forgot-password", json={"email": email}, timeout=30)
    assert r.status_code == 200
    time.sleep(0.3)
    cli = MongoClient(MONGO_URL)
    db = cli[DB_NAME]
    doc = db.reset_tokens.find_one({"user_id": uid, "used": False}, sort=[("created_at", -1)])
    assert doc, "reset_token not created"
    token = doc["token"]

    # invalid token -> 400
    bad = requests.post(f"{API}/auth/reset-password", json={"token": "bogus", "new_password": "NewPass123!"})
    assert bad.status_code == 400

    # valid token -> ok, new password works
    ok = requests.post(f"{API}/auth/reset-password", json={"token": token, "new_password": "NewPass123!"})
    assert ok.status_code == 200
    assert requests.post(f"{API}/auth/login", json={"email": email, "password": "NewPass123!"}).status_code == 200
    assert requests.post(f"{API}/auth/login", json={"email": email, "password": pw}).status_code == 401

    # single-use
    reuse = requests.post(f"{API}/auth/reset-password", json={"token": token, "new_password": "NewPass999!"})
    assert reuse.status_code == 400


# ---------- View count: increments by exactly 1 ----------
def test_view_count_increments_by_one():
    tok = _login(**ADMIN)
    body = {"type": "html", "title": "TEST_r7_view", "subject": "mathematics", "grade": "1-4",
            "description": "", "html_code": "<html><body>x</body></html>", "tags": []}
    cr = requests.post(f"{API}/tasks", headers=_auth(tok), json=body)
    assert cr.status_code == 200, cr.text
    tid = cr.json()["id"]
    v0 = requests.get(f"{API}/tasks/{tid}").json()["views"]
    requests.post(f"{API}/tasks/{tid}/view")
    v1 = requests.get(f"{API}/tasks/{tid}").json()["views"]
    assert v1 == v0 + 1
    # cleanup
    requests.delete(f"{API}/tasks/{tid}", headers=_auth(tok))


# ---------- Comments: logged-in post+delete; guests cannot post ----------
def test_comments_create_delete_and_guest_blocked():
    atok = _login(**ADMIN)
    body = {"type": "blog", "title": "TEST_r7_comments", "subject": "other", "grade": "1-4",
            "description": "", "body": "hello", "tags": []}
    cr = requests.post(f"{API}/tasks", headers=_auth(atok), json=body)
    tid = cr.json()["id"]

    _, _, utok, _ = _register("TEST R7 Commenter")
    # guest cannot post
    g = requests.post(f"{API}/tasks/{tid}/comments", json={"body": "nope"})
    assert g.status_code == 401

    c = requests.post(f"{API}/tasks/{tid}/comments", headers=_auth(utok), json={"body": "hi there"})
    assert c.status_code == 200
    cid = c.json()["id"]
    lst = requests.get(f"{API}/tasks/{tid}/comments").json()
    assert any(x["id"] == cid for x in lst)

    # author of comment can delete
    d = requests.delete(f"{API}/comments/{cid}", headers=_auth(utok))
    assert d.status_code == 200

    requests.delete(f"{API}/tasks/{tid}", headers=_auth(atok))


# ---------- Pinned + highlight: admin can set; feed returns pinned first ----------
def test_pin_and_highlight_appear_first_in_feed():
    tok = _login(**ADMIN)
    base = {"type": "blog", "subject": "other", "grade": "1-4", "description": "", "body": "x", "tags": []}
    regular = requests.post(f"{API}/tasks", headers=_auth(tok), json={**base, "title": "TEST_r7 regular"}).json()
    pinned = requests.post(f"{API}/tasks", headers=_auth(tok),
                           json={**base, "title": "TEST_r7 PINNED", "pinned": True, "highlight_color": "#FDE68A"}).json()
    assert pinned["pinned"] is True
    assert pinned["highlight_color"] == "#FDE68A"

    feed = requests.get(f"{API}/tasks?limit=20").json()["items"]
    # Find positions of our two posts
    titles = [x["title"] for x in feed]
    assert "TEST_r7 PINNED" in titles
    # Pinned must appear before non-pinned regular within returned page
    if "TEST_r7 regular" in titles:
        assert titles.index("TEST_r7 PINNED") < titles.index("TEST_r7 regular")

    requests.delete(f"{API}/tasks/{pinned['id']}", headers=_auth(tok))
    requests.delete(f"{API}/tasks/{regular['id']}", headers=_auth(tok))


# ---------- Folder creation (used by inline create in Publish) ----------
def test_folder_create_and_list():
    _, _, utok, _ = _register("TEST R7 Folder")
    r = requests.post(f"{API}/folders", headers=_auth(utok), json={"name": "TEST_r7 folder"})
    assert r.status_code == 200
    fid = r.json()["id"]
    lst = requests.get(f"{API}/folders", headers=_auth(utok)).json()
    assert any(f["id"] == fid for f in lst)
