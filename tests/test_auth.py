"""Tests for authentication endpoints and profile ownership filtering."""
import json
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))


def _auth_headers(client, username: str, password: str = "password123") -> dict:
    """Register (or login) and return auth headers."""
    resp = client.post("/api/auth/register", json={"username": username, "password": password})
    if resp.status_code == 400:  # already exists
        resp = client.post("/api/auth/login", data={"username": username, "password": password})
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


class TestRegister:
    def test_register_success(self, client):
        resp = client.post("/api/auth/register", json={
            "username": "newuser_reg", "password": "password123", "email": "reg@example.com"
        })
        assert resp.status_code == 201
        body = resp.json()
        assert "access_token" in body
        assert body["token_type"] == "bearer"
        assert body["username"] == "newuser_reg"
        assert "user_id" in body

    def test_register_duplicate_username(self, client):
        client.post("/api/auth/register", json={"username": "dup_user", "password": "password123"})
        resp = client.post("/api/auth/register", json={"username": "dup_user", "password": "password456"})
        assert resp.status_code == 400
        assert "taken" in resp.json()["detail"].lower()

    def test_register_short_password(self, client):
        resp = client.post("/api/auth/register", json={"username": "shortpw", "password": "abc"})
        assert resp.status_code == 400

    def test_register_empty_username(self, client):
        resp = client.post("/api/auth/register", json={"username": "   ", "password": "password123"})
        assert resp.status_code == 400


class TestLogin:
    def test_login_success(self, client):
        client.post("/api/auth/register", json={"username": "loginok", "password": "testpass1"})
        resp = client.post("/api/auth/login", data={"username": "loginok", "password": "testpass1"})
        assert resp.status_code == 200
        body = resp.json()
        assert "access_token" in body
        assert body["username"] == "loginok"

    def test_login_wrong_password(self, client):
        client.post("/api/auth/register", json={"username": "badpw_user", "password": "correct"})
        resp = client.post("/api/auth/login", data={"username": "badpw_user", "password": "wrong"})
        assert resp.status_code == 401

    def test_login_unknown_user(self, client):
        resp = client.post("/api/auth/login", data={"username": "nobody_exists", "password": "pass"})
        assert resp.status_code == 401


class TestMeEndpoint:
    def test_me_authenticated(self, client):
        resp = client.post("/api/auth/register", json={"username": "me_user", "password": "password123"})
        token = resp.json()["access_token"]
        me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert me.status_code == 200
        body = me.json()
        assert body["username"] == "me_user"
        assert "user_id" in body

    def test_me_unauthenticated(self, client):
        resp = client.get("/api/auth/me")
        assert resp.status_code == 401

    def test_me_invalid_token(self, client):
        resp = client.get("/api/auth/me", headers={"Authorization": "Bearer not.a.real.token"})
        assert resp.status_code == 401


class TestProfileOwnership:
    def test_import_associates_profile_with_user(self, client):
        headers = _auth_headers(client, "owner_user")
        data = json.dumps({"full_name": "Owner's Profile"}).encode()
        imp = client.post(
            "/api/import",
            files={"file": ("p.json", data, "application/json")},
            headers=headers,
        )
        assert imp.status_code == 201
        pid = imp.json()["profile_id"]

        # Profile should appear in this user's list
        profiles = client.get("/api/profiles", headers=headers).json()
        assert any(p["id"] == pid for p in profiles)

    def test_other_user_cannot_see_profile_in_list(self, client):
        h_a = _auth_headers(client, "visibility_a")
        h_b = _auth_headers(client, "visibility_b")

        data = json.dumps({"full_name": "Private Profile"}).encode()
        client.post(
            "/api/import",
            files={"file": ("p.json", data, "application/json")},
            headers=h_a,
        )

        profiles_b = client.get("/api/profiles", headers=h_b).json()
        assert not any(p["full_name"] == "Private Profile" for p in profiles_b)

    def test_unauthenticated_sees_all_profiles(self, client):
        """After auth enforcement, unauthenticated GET /profiles returns 401."""
        resp = client.get("/api/profiles")
        assert resp.status_code == 401

    def test_each_user_only_sees_own_profiles(self, client):
        h1 = _auth_headers(client, "iso_user1")
        h2 = _auth_headers(client, "iso_user2")

        d1 = json.dumps({"full_name": "Iso User One Profile"}).encode()
        d2 = json.dumps({"full_name": "Iso User Two Profile"}).encode()

        client.post("/api/import", files={"file": ("a.json", d1, "application/json")}, headers=h1)
        client.post("/api/import", files={"file": ("b.json", d2, "application/json")}, headers=h2)

        p1 = client.get("/api/profiles", headers=h1).json()
        p2 = client.get("/api/profiles", headers=h2).json()

        names1 = [p["full_name"] for p in p1]
        names2 = [p["full_name"] for p in p2]

        assert "Iso User One Profile" in names1
        assert "Iso User Two Profile" not in names1
        assert "Iso User Two Profile" in names2
        assert "Iso User One Profile" not in names2


class TestProfileRouterAuth:
    """Profile routes must require auth after enforcement."""

    def test_list_profiles_no_token_returns_401(self, client):
        resp = client.get("/api/profiles")
        assert resp.status_code == 401

    def test_get_profile_no_token_returns_401(self, client):
        headers = _auth_headers(client, "pauth_creator")
        data = json.dumps({"full_name": "Auth Test Profile"}).encode()
        imp = client.post(
            "/api/import",
            files={"file": ("p.json", data, "application/json")},
            headers=headers,
        )
        pid = imp.json()["profile_id"]
        resp = client.get(f"/api/profiles/{pid}")
        assert resp.status_code == 401

    def test_patch_profile_no_token_returns_401(self, client):
        headers = _auth_headers(client, "pauth_patcher")
        data = json.dumps({"full_name": "Patch Test"}).encode()
        imp = client.post(
            "/api/import",
            files={"file": ("p.json", data, "application/json")},
            headers=headers,
        )
        pid = imp.json()["profile_id"]
        resp = client.patch(f"/api/profiles/{pid}", json={"full_name": "New Name"})
        assert resp.status_code == 401

    def test_delete_profile_no_token_returns_401(self, client):
        headers = _auth_headers(client, "pauth_deleter")
        data = json.dumps({"full_name": "Del Test"}).encode()
        imp = client.post(
            "/api/import",
            files={"file": ("p.json", data, "application/json")},
            headers=headers,
        )
        pid = imp.json()["profile_id"]
        resp = client.delete(f"/api/profiles/{pid}")
        assert resp.status_code == 401

    def test_wrong_user_get_profile_returns_403(self, client):
        h_a = _auth_headers(client, "pauth_owner_a")
        h_b = _auth_headers(client, "pauth_owner_b")
        data = json.dumps({"full_name": "A Profile"}).encode()
        imp = client.post(
            "/api/import",
            files={"file": ("p.json", data, "application/json")},
            headers=h_a,
        )
        pid = imp.json()["profile_id"]
        resp = client.get(f"/api/profiles/{pid}", headers=h_b)
        assert resp.status_code == 403

    def test_wrong_user_delete_profile_returns_403(self, client):
        h_a = _auth_headers(client, "pauth_del_a")
        h_b = _auth_headers(client, "pauth_del_b")
        data = json.dumps({"full_name": "A Profile 2"}).encode()
        imp = client.post(
            "/api/import",
            files={"file": ("p.json", data, "application/json")},
            headers=h_a,
        )
        pid = imp.json()["profile_id"]
        resp = client.delete(f"/api/profiles/{pid}", headers=h_b)
        assert resp.status_code == 403

    def test_wrong_user_patch_profile_returns_403(self, client):
        h_a = _auth_headers(client, "pauth_patch_a")
        h_b = _auth_headers(client, "pauth_patch_b")
        data = json.dumps({"full_name": "A Patch Profile"}).encode()
        imp = client.post(
            "/api/import",
            files={"file": ("p.json", data, "application/json")},
            headers=h_a,
        )
        pid = imp.json()["profile_id"]
        resp = client.patch(f"/api/profiles/{pid}", json={"full_name": "Hacked"}, headers=h_b)
        assert resp.status_code == 403

    def test_owner_can_get_profile(self, client):
        headers = _auth_headers(client, "pauth_own_get")
        data = json.dumps({"full_name": "Owner Profile"}).encode()
        imp = client.post(
            "/api/import",
            files={"file": ("p.json", data, "application/json")},
            headers=headers,
        )
        pid = imp.json()["profile_id"]
        resp = client.get(f"/api/profiles/{pid}", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["full_name"] == "Owner Profile"


class TestAnalysisRouterAuth:
    """Analysis routes must require auth."""

    def _make_profile(self, client, username: str) -> tuple[dict, int]:
        headers = _auth_headers(client, username)
        data = json.dumps({"full_name": f"{username} Profile"}).encode()
        imp = client.post(
            "/api/import",
            files={"file": ("p.json", data, "application/json")},
            headers=headers,
        )
        return headers, imp.json()["profile_id"]

    def test_analyze_no_token_returns_401(self, client):
        _, pid = self._make_profile(client, "ana_creator_1")
        resp = client.post(f"/api/profiles/{pid}/analyze")
        assert resp.status_code == 401

    def test_cover_letter_no_token_returns_401(self, client):
        _, pid = self._make_profile(client, "ana_creator_2")
        resp = client.post(
            f"/api/profiles/{pid}/cover-letter",
            json={"job_title": "Dev", "company": "Acme"},
        )
        assert resp.status_code == 401

    def test_list_cover_letters_no_token_returns_401(self, client):
        _, pid = self._make_profile(client, "ana_creator_3")
        resp = client.get(f"/api/profiles/{pid}/cover-letters")
        assert resp.status_code == 401

    def test_roadmap_no_token_returns_401(self, client):
        _, pid = self._make_profile(client, "ana_creator_4")
        resp = client.post(f"/api/profiles/{pid}/roadmap", json={})
        assert resp.status_code == 401

    def test_list_roadmaps_no_token_returns_401(self, client):
        _, pid = self._make_profile(client, "ana_creator_5")
        resp = client.get(f"/api/profiles/{pid}/roadmaps")
        assert resp.status_code == 401

    def test_wrong_user_list_cover_letters_returns_403(self, client):
        h_a = _auth_headers(client, "ana_owner_a")
        h_b = _auth_headers(client, "ana_owner_b")
        data = json.dumps({"full_name": "CL Profile"}).encode()
        imp = client.post(
            "/api/import",
            files={"file": ("p.json", data, "application/json")},
            headers=h_a,
        )
        pid = imp.json()["profile_id"]
        resp = client.get(f"/api/profiles/{pid}/cover-letters", headers=h_b)
        assert resp.status_code == 403

    def test_wrong_user_list_roadmaps_returns_403(self, client):
        h_a = _auth_headers(client, "ana_rm_owner_a")
        h_b = _auth_headers(client, "ana_rm_owner_b")
        data = json.dumps({"full_name": "Roadmap Profile"}).encode()
        imp = client.post(
            "/api/import",
            files={"file": ("p.json", data, "application/json")},
            headers=h_a,
        )
        pid = imp.json()["profile_id"]
        resp = client.get(f"/api/profiles/{pid}/roadmaps", headers=h_b)
        assert resp.status_code == 403


class TestExportRouterAuth:
    """Export route must require auth and respect ownership."""

    def _make_profile(self, client, username: str) -> tuple[dict, int]:
        headers = _auth_headers(client, username)
        data = json.dumps({"full_name": f"{username} Profile"}).encode()
        imp = client.post(
            "/api/import",
            files={"file": ("p.json", data, "application/json")},
            headers=headers,
        )
        return headers, imp.json()["profile_id"]

    def test_export_no_token_returns_401(self, client):
        _, pid = self._make_profile(client, "exp_creator")
        resp = client.get(f"/api/profiles/{pid}/export/json")
        assert resp.status_code == 401

    def test_export_wrong_user_returns_403(self, client):
        h_a = _auth_headers(client, "exp_owner_a")
        h_b = _auth_headers(client, "exp_owner_b")
        data = json.dumps({"full_name": "Export Profile"}).encode()
        imp = client.post(
            "/api/import",
            files={"file": ("p.json", data, "application/json")},
            headers=h_a,
        )
        pid = imp.json()["profile_id"]
        resp = client.get(f"/api/profiles/{pid}/export/json", headers=h_b)
        assert resp.status_code == 403

    def test_export_owner_returns_200(self, client):
        headers = _auth_headers(client, "exp_owner_200")
        data = json.dumps({"full_name": "Export Owner Profile"}).encode()
        imp = client.post(
            "/api/import",
            files={"file": ("p.json", data, "application/json")},
            headers=headers,
        )
        pid = imp.json()["profile_id"]
        resp = client.get(f"/api/profiles/{pid}/export/json", headers=headers)
        assert resp.status_code == 200
        assert "application/json" in resp.headers["content-type"]
