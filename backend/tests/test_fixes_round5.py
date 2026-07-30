"""Round-5 tests: separate hide_followers/hide_following and avatar/bio."""
import io
import os
import time
import pytest
import requests
from pathlib import Path

BASE = None
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
    tok = r.json()["token"]
    yield tok
    # cleanup: restore hide flags & avatar/bio
    requests.put(f"{API}/users/me",
                 json={"hide_followers": False, "hide_following": False,
                       "bio": "", "avatar_file_id": ""},
                 headers=h(tok))


@pytest.fixture(scope="module")
def teacher_id(teacher_token):
    return requests.get(f"{API}/auth/me", headers=h(teacher_token)).json()["id"]


@pytest.fixture(scope="module")
def other_user():
    email = f"test_r5_{int(time.time())}@example.com"
    r = requests.post(f"{API}/auth/register",
                      json={"email": email, "password": "abcd1234", "name": "TEST_R5"})
    assert r.status_code == 200, r.text
    tok = r.json()["token"]
    uid = r.json()["user"]["id"]
    yield {"token": tok, "id": uid}
    requests.delete(f"{API}/users/me", headers=h(tok))


class TestSplitHideFollows:
    def test_hide_followers_only(self, teacher_token, teacher_id, other_user):
        # ensure some counts
        requests.post(f"{API}/users/{teacher_id}/follow", headers=h(other_user["token"]))
        # teacher follows other so following_count>0
        requests.post(f"{API}/users/{other_user['id']}/follow", headers=h(teacher_token))
        try:
            u = requests.put(f"{API}/users/me",
                             json={"hide_followers": True, "hide_following": False},
                             headers=h(teacher_token))
            assert u.status_code == 200
            assert u.json().get("hide_followers") is True
            assert u.json().get("hide_following") is False

            prof = requests.get(f"{API}/users/{teacher_id}",
                                headers=h(other_user["token"])).json()
            assert prof["hide_followers"] is True
            assert prof["hide_following"] is False
            assert prof["followers_count"] is None
            assert isinstance(prof["following_count"], int) and prof["following_count"] >= 1

            fl = requests.get(f"{API}/users/{teacher_id}/followers",
                              headers=h(other_user["token"])).json()
            assert fl == []
            fg = requests.get(f"{API}/users/{teacher_id}/following",
                              headers=h(other_user["token"])).json()
            assert isinstance(fg, list) and len(fg) >= 1

            # Owner still sees own
            self_prof = requests.get(f"{API}/users/{teacher_id}",
                                     headers=h(teacher_token)).json()
            assert self_prof["followers_count"] is not None and self_prof["followers_count"] >= 1
            own_fl = requests.get(f"{API}/users/{teacher_id}/followers",
                                  headers=h(teacher_token)).json()
            assert len(own_fl) >= 1
        finally:
            requests.put(f"{API}/users/me",
                         json={"hide_followers": False, "hide_following": False},
                         headers=h(teacher_token))
            requests.post(f"{API}/users/{teacher_id}/follow", headers=h(other_user["token"]))  # unfollow
            requests.post(f"{API}/users/{other_user['id']}/follow", headers=h(teacher_token))  # unfollow

    def test_hide_following_only(self, teacher_token, teacher_id, other_user):
        requests.post(f"{API}/users/{teacher_id}/follow", headers=h(other_user["token"]))
        requests.post(f"{API}/users/{other_user['id']}/follow", headers=h(teacher_token))
        try:
            u = requests.put(f"{API}/users/me",
                             json={"hide_followers": False, "hide_following": True},
                             headers=h(teacher_token))
            assert u.status_code == 200
            assert u.json().get("hide_following") is True
            assert u.json().get("hide_followers") is False

            prof = requests.get(f"{API}/users/{teacher_id}",
                                headers=h(other_user["token"])).json()
            assert prof["hide_following"] is True
            assert prof["hide_followers"] is False
            assert prof["following_count"] is None
            assert isinstance(prof["followers_count"], int) and prof["followers_count"] >= 1

            fg = requests.get(f"{API}/users/{teacher_id}/following",
                              headers=h(other_user["token"])).json()
            assert fg == []
            fl = requests.get(f"{API}/users/{teacher_id}/followers",
                              headers=h(other_user["token"])).json()
            assert isinstance(fl, list) and len(fl) >= 1
        finally:
            requests.put(f"{API}/users/me",
                         json={"hide_followers": False, "hide_following": False},
                         headers=h(teacher_token))
            requests.post(f"{API}/users/{teacher_id}/follow", headers=h(other_user["token"]))
            requests.post(f"{API}/users/{other_user['id']}/follow", headers=h(teacher_token))


class TestAvatarAndBio:
    def test_upload_avatar_and_update_profile(self, teacher_token, teacher_id):
        # 1x1 PNG
        png_bytes = bytes.fromhex(
            "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
            "0000000d49444154789c626001000000ffff03000006000557bfabd40000000049454e44ae426082"
        )
        files = {"file": ("avatar.png", io.BytesIO(png_bytes), "image/png")}
        r = requests.post(f"{API}/upload", files=files, headers=h(teacher_token))
        assert r.status_code == 200, r.text
        j = r.json()
        assert j.get("is_image") is True
        fid = j["file_id"]

        bio = "TEST_bio_r5 " + str(int(time.time()))
        u = requests.put(f"{API}/users/me",
                         json={"bio": bio, "avatar_file_id": fid},
                         headers=h(teacher_token))
        assert u.status_code == 200
        assert u.json()["bio"] == bio
        assert u.json()["avatar_file_id"] == fid
        assert u.json()["avatar_url"]

        me = requests.get(f"{API}/auth/me", headers=h(teacher_token)).json()
        assert me["bio"] == bio
        assert me["avatar_file_id"] == fid
        assert me["avatar_url"].endswith(f"/files/{fid}")

        # Public profile also exposes them
        pub = requests.get(f"{API}/users/{teacher_id}").json()
        assert pub["bio"] == bio
        assert pub["avatar_url"] and fid in pub["avatar_url"]

    def test_avatar_visible_in_follower_list(self, teacher_token, teacher_id, other_user):
        # Ensure avatar set from previous test; ensure other follows teacher
        requests.post(f"{API}/users/{teacher_id}/follow", headers=h(other_user["token"]))
        try:
            fl = requests.get(f"{API}/users/{teacher_id}/followers",
                              headers=h(other_user["token"])).json()
            assert isinstance(fl, list)
            # teacher is in "followers" -> from other_user perspective, they'd appear in other_user's following list.
            fg = requests.get(f"{API}/users/{other_user['id']}/following",
                              headers=h(other_user["token"])).json()
            # find teacher entry
            teacher_entry = next((x for x in fg if x["id"] == teacher_id), None)
            assert teacher_entry is not None
            assert teacher_entry.get("avatar_url")
        finally:
            requests.post(f"{API}/users/{teacher_id}/follow", headers=h(other_user["token"]))

    def test_clear_bio_and_avatar(self, teacher_token):
        u = requests.put(f"{API}/users/me",
                         json={"bio": "", "avatar_file_id": ""},
                         headers=h(teacher_token))
        assert u.status_code == 200
        assert u.json()["bio"] == ""
        assert not u.json().get("avatar_file_id")
        assert not u.json().get("avatar_url")
