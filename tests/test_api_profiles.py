"""Tests for profile CRUD and section editing endpoints."""
import json
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))


def _get_auth_headers(client, username: str = "testuser", password: str = "password123") -> dict:
    """Register (or login if already exists) and return auth headers."""
    resp = client.post(
        "/api/auth/register",
        json={"username": username, "password": password, "email": f"{username}@test.local"},
    )
    if resp.status_code == 400:  # already registered
        resp = client.post("/api/auth/login", data={"username": username, "password": password})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _sections_headers(client) -> dict:
    """Auth headers for section-editing tests (NULL user_id profiles allow any auth'd user)."""
    return _get_auth_headers(client, "sections_default_user")


def _create_profile(client, headers: dict = None) -> int:
    """Helper: import a minimal JSON to get a profile_id."""
    data = json.dumps({
        "full_name": "Test User",
        "email": "test@example.com",
        "phone": "+1 555 0000",
        "skills": [{"name": "Python", "category": "Language", "years": 3}],
        "experience": [{"company": "Acme", "role": "Dev", "start": "2020", "end": "2023"}],
        "projects": [{"name": "TestApp", "description": "A test app", "tech": ["React"]}],
        "education": [{"institution": "MIT", "degree": "BSc", "field": "CS", "start": "2016", "end": "2020"}],
        "certifications": [{"name": "AWS SAA", "issuer": "Amazon", "date": "2022"}],
    }).encode()
    resp = client.post(
        "/api/import",
        files={"file": ("p.json", data, "application/json")},
        headers=headers,
    )
    assert resp.status_code == 201
    return resp.json()["profile_id"]


class TestProfileCRUD:
    def test_list_profiles(self, client):
        headers = _get_auth_headers(client, "crud_list_user")
        resp = client.get("/api/profiles", headers=headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_get_profile(self, client):
        headers = _get_auth_headers(client, "crud_get_user")
        pid = _create_profile(client, headers)
        resp = client.get(f"/api/profiles/{pid}", headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["full_name"] == "Test User"
        assert body["email"] == "test@example.com"

    def test_patch_profile(self, client):
        headers = _get_auth_headers(client, "crud_patch_user")
        pid = _create_profile(client, headers)
        resp = client.patch(f"/api/profiles/{pid}", json={"full_name": "Updated Name"}, headers=headers)
        assert resp.status_code == 200
        assert resp.json()["full_name"] == "Updated Name"

    def test_get_nonexistent_profile(self, client):
        headers = _get_auth_headers(client, "crud_nonexist_user")
        resp = client.get("/api/profiles/99999", headers=headers)
        assert resp.status_code == 404

    def test_delete_profile(self, client):
        headers = _get_auth_headers(client, "crud_delete_user")
        pid = _create_profile(client, headers)
        resp = client.delete(f"/api/profiles/{pid}", headers=headers)
        assert resp.status_code == 204
        resp2 = client.get(f"/api/profiles/{pid}", headers=headers)
        assert resp2.status_code == 404


class TestSkillsCRUD:
    def test_add_skill(self, client):
        headers = _sections_headers(client)
        pid = _create_profile(client, headers)
        resp = client.post(f"/api/profiles/{pid}/skills", json={"name": "FastAPI", "category": "Framework", "years": 2}, headers=headers)
        assert resp.status_code == 201
        body = resp.json()
        assert body["name"] == "FastAPI"
        assert body["id"] is not None

    def test_update_skill(self, client):
        headers = _sections_headers(client)
        pid = _create_profile(client, headers)
        add_resp = client.post(f"/api/profiles/{pid}/skills", json={"name": "Go", "category": "Language", "years": 1}, headers=headers)
        skill_id = add_resp.json()["id"]
        patch_resp = client.patch(f"/api/profiles/{pid}/skills/{skill_id}", json={"years": 3.5}, headers=headers)
        assert patch_resp.status_code == 200
        assert patch_resp.json()["years"] == 3.5

    def test_delete_skill(self, client):
        headers = _sections_headers(client)
        pid = _create_profile(client, headers)
        add_resp = client.post(f"/api/profiles/{pid}/skills", json={"name": "Rust", "category": "Language", "years": 1}, headers=headers)
        skill_id = add_resp.json()["id"]
        del_resp = client.delete(f"/api/profiles/{pid}/skills/{skill_id}", headers=headers)
        assert del_resp.status_code == 204

    def test_skill_wrong_profile(self, client):
        headers = _sections_headers(client)
        pid1 = _create_profile(client, headers)
        pid2 = _create_profile(client, headers)
        add_resp = client.post(f"/api/profiles/{pid1}/skills", json={"name": "Kotlin"}, headers=headers)
        skill_id = add_resp.json()["id"]
        resp = client.delete(f"/api/profiles/{pid2}/skills/{skill_id}", headers=headers)
        assert resp.status_code == 404


class TestExperienceCRUD:
    def test_add_experience(self, client):
        headers = _sections_headers(client)
        pid = _create_profile(client, headers)
        resp = client.post(f"/api/profiles/{pid}/experience", json={
            "company": "NewCo", "role": "CTO", "start": "2024", "end": "", "location": "Remote", "bullets": []
        }, headers=headers)
        assert resp.status_code == 201
        assert resp.json()["company"] == "NewCo"

    def test_update_experience(self, client):
        headers = _sections_headers(client)
        pid = _create_profile(client, headers)
        add_resp = client.post(f"/api/profiles/{pid}/experience", json={
            "company": "Corp", "role": "Engineer", "start": "2021", "end": "2023", "location": ""
        }, headers=headers)
        exp_id = add_resp.json()["id"]
        patch_resp = client.patch(f"/api/profiles/{pid}/experience/{exp_id}", json={"role": "Senior Engineer"}, headers=headers)
        assert patch_resp.status_code == 200
        assert patch_resp.json()["role"] == "Senior Engineer"

    def test_delete_experience(self, client):
        headers = _sections_headers(client)
        pid = _create_profile(client, headers)
        add_resp = client.post(f"/api/profiles/{pid}/experience", json={"company": "X", "role": "Y", "start": "2022"}, headers=headers)
        exp_id = add_resp.json()["id"]
        resp = client.delete(f"/api/profiles/{pid}/experience/{exp_id}", headers=headers)
        assert resp.status_code == 204

    def test_add_bullet(self, client):
        headers = _sections_headers(client)
        pid = _create_profile(client, headers)
        exp_resp = client.post(f"/api/profiles/{pid}/experience", json={"company": "A", "role": "B", "start": "2020"}, headers=headers)
        exp_id = exp_resp.json()["id"]
        resp = client.post(f"/api/profiles/{pid}/experience/{exp_id}/bullets", json={"text": "Built cool things"}, headers=headers)
        assert resp.status_code == 201
        assert resp.json()["text"] == "Built cool things"

    def test_update_bullet(self, client):
        headers = _sections_headers(client)
        pid = _create_profile(client, headers)
        exp_resp = client.post(f"/api/profiles/{pid}/experience", json={"company": "A", "role": "B", "start": "2020"}, headers=headers)
        exp_id = exp_resp.json()["id"]
        b_resp = client.post(f"/api/profiles/{pid}/experience/{exp_id}/bullets", json={"text": "Original"}, headers=headers)
        bid = b_resp.json()["id"]
        patch = client.patch(f"/api/profiles/{pid}/experience/{exp_id}/bullets/{bid}", json={"text": "Updated"}, headers=headers)
        assert patch.status_code == 200
        assert patch.json()["text"] == "Updated"

    def test_delete_bullet(self, client):
        headers = _sections_headers(client)
        pid = _create_profile(client, headers)
        exp_resp = client.post(f"/api/profiles/{pid}/experience", json={"company": "A", "role": "B", "start": "2020"}, headers=headers)
        exp_id = exp_resp.json()["id"]
        b_resp = client.post(f"/api/profiles/{pid}/experience/{exp_id}/bullets", json={"text": "Delete me"}, headers=headers)
        bid = b_resp.json()["id"]
        resp = client.delete(f"/api/profiles/{pid}/experience/{exp_id}/bullets/{bid}", headers=headers)
        assert resp.status_code == 204


class TestProjectsCRUD:
    def test_add_project(self, client):
        headers = _sections_headers(client)
        pid = _create_profile(client, headers)
        resp = client.post(f"/api/profiles/{pid}/projects", json={
            "name": "CareerBot", "description": "AI bot", "link": "https://github.com/x", "tech": ["Python", "FastAPI"]
        }, headers=headers)
        assert resp.status_code == 201
        body = resp.json()
        assert body["name"] == "CareerBot"
        assert "Python" in body["tech"]

    def test_update_project(self, client):
        headers = _sections_headers(client)
        pid = _create_profile(client, headers)
        add = client.post(f"/api/profiles/{pid}/projects", json={"name": "Proj", "tech": ["Go"]}, headers=headers)
        proj_id = add.json()["id"]
        patch = client.patch(f"/api/profiles/{pid}/projects/{proj_id}", json={"name": "Updated Proj"}, headers=headers)
        assert patch.status_code == 200
        assert patch.json()["name"] == "Updated Proj"

    def test_delete_project(self, client):
        headers = _sections_headers(client)
        pid = _create_profile(client, headers)
        add = client.post(f"/api/profiles/{pid}/projects", json={"name": "ToDelete"}, headers=headers)
        proj_id = add.json()["id"]
        resp = client.delete(f"/api/profiles/{pid}/projects/{proj_id}", headers=headers)
        assert resp.status_code == 204


class TestEducationCRUD:
    def test_add_education(self, client):
        headers = _sections_headers(client)
        pid = _create_profile(client, headers)
        resp = client.post(f"/api/profiles/{pid}/education", json={
            "institution": "Stanford", "degree": "MSc", "field": "AI", "start": "2018", "end": "2020"
        }, headers=headers)
        assert resp.status_code == 201
        assert resp.json()["institution"] == "Stanford"

    def test_update_education(self, client):
        headers = _sections_headers(client)
        pid = _create_profile(client, headers)
        add = client.post(f"/api/profiles/{pid}/education", json={"institution": "Oxford", "degree": "PhD"}, headers=headers)
        edu_id = add.json()["id"]
        patch = client.patch(f"/api/profiles/{pid}/education/{edu_id}", json={"field": "NLP"}, headers=headers)
        assert patch.status_code == 200
        assert patch.json()["field"] == "NLP"

    def test_delete_education(self, client):
        headers = _sections_headers(client)
        pid = _create_profile(client, headers)
        add = client.post(f"/api/profiles/{pid}/education", json={"institution": "Harvard"}, headers=headers)
        edu_id = add.json()["id"]
        resp = client.delete(f"/api/profiles/{pid}/education/{edu_id}", headers=headers)
        assert resp.status_code == 204


class TestCertificationsCRUD:
    def test_add_certification(self, client):
        headers = _sections_headers(client)
        pid = _create_profile(client, headers)
        resp = client.post(f"/api/profiles/{pid}/certifications", json={
            "name": "GCP Professional", "issuer": "Google", "date": "2023-06"
        }, headers=headers)
        assert resp.status_code == 201
        assert resp.json()["name"] == "GCP Professional"

    def test_update_certification(self, client):
        headers = _sections_headers(client)
        pid = _create_profile(client, headers)
        add = client.post(f"/api/profiles/{pid}/certifications", json={"name": "Azure", "issuer": "Microsoft"}, headers=headers)
        cert_id = add.json()["id"]
        patch = client.patch(f"/api/profiles/{pid}/certifications/{cert_id}", json={"date": "2024-01"}, headers=headers)
        assert patch.status_code == 200
        assert patch.json()["date"] == "2024-01"

    def test_delete_certification(self, client):
        headers = _sections_headers(client)
        pid = _create_profile(client, headers)
        add = client.post(f"/api/profiles/{pid}/certifications", json={"name": "ToDelete"}, headers=headers)
        cert_id = add.json()["id"]
        resp = client.delete(f"/api/profiles/{pid}/certifications/{cert_id}", headers=headers)
        assert resp.status_code == 204
