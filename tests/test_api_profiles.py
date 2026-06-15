"""Tests for profile CRUD and section editing endpoints."""
import json
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))


def _create_profile(client) -> int:
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
    resp = client.post("/api/import", files={"file": ("p.json", data, "application/json")})
    assert resp.status_code == 201
    return resp.json()["profile_id"]


class TestProfileCRUD:
    def test_list_profiles(self, client):
        resp = client.get("/api/profiles")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_get_profile(self, client):
        pid = _create_profile(client)
        resp = client.get(f"/api/profiles/{pid}")
        assert resp.status_code == 200
        body = resp.json()
        assert body["full_name"] == "Test User"
        assert body["email"] == "test@example.com"

    def test_patch_profile(self, client):
        pid = _create_profile(client)
        resp = client.patch(f"/api/profiles/{pid}", json={"full_name": "Updated Name"})
        assert resp.status_code == 200
        assert resp.json()["full_name"] == "Updated Name"

    def test_get_nonexistent_profile(self, client):
        resp = client.get("/api/profiles/99999")
        assert resp.status_code == 404

    def test_delete_profile(self, client):
        pid = _create_profile(client)
        resp = client.delete(f"/api/profiles/{pid}")
        assert resp.status_code == 204
        resp2 = client.get(f"/api/profiles/{pid}")
        assert resp2.status_code == 404


class TestSkillsCRUD:
    def test_add_skill(self, client):
        pid = _create_profile(client)
        resp = client.post(f"/api/profiles/{pid}/skills", json={"name": "FastAPI", "category": "Framework", "years": 2})
        assert resp.status_code == 201
        body = resp.json()
        assert body["name"] == "FastAPI"
        assert body["id"] is not None

    def test_update_skill(self, client):
        pid = _create_profile(client)
        add_resp = client.post(f"/api/profiles/{pid}/skills", json={"name": "Go", "category": "Language", "years": 1})
        skill_id = add_resp.json()["id"]
        patch_resp = client.patch(f"/api/profiles/{pid}/skills/{skill_id}", json={"years": 3.5})
        assert patch_resp.status_code == 200
        assert patch_resp.json()["years"] == 3.5

    def test_delete_skill(self, client):
        pid = _create_profile(client)
        add_resp = client.post(f"/api/profiles/{pid}/skills", json={"name": "Rust", "category": "Language", "years": 1})
        skill_id = add_resp.json()["id"]
        del_resp = client.delete(f"/api/profiles/{pid}/skills/{skill_id}")
        assert del_resp.status_code == 204

    def test_skill_wrong_profile(self, client):
        pid1 = _create_profile(client)
        pid2 = _create_profile(client)
        add_resp = client.post(f"/api/profiles/{pid1}/skills", json={"name": "Kotlin"})
        skill_id = add_resp.json()["id"]
        resp = client.delete(f"/api/profiles/{pid2}/skills/{skill_id}")
        assert resp.status_code == 404


class TestExperienceCRUD:
    def test_add_experience(self, client):
        pid = _create_profile(client)
        resp = client.post(f"/api/profiles/{pid}/experience", json={
            "company": "NewCo", "role": "CTO", "start": "2024", "end": "", "location": "Remote", "bullets": []
        })
        assert resp.status_code == 201
        assert resp.json()["company"] == "NewCo"

    def test_update_experience(self, client):
        pid = _create_profile(client)
        add_resp = client.post(f"/api/profiles/{pid}/experience", json={
            "company": "Corp", "role": "Engineer", "start": "2021", "end": "2023", "location": ""
        })
        exp_id = add_resp.json()["id"]
        patch_resp = client.patch(f"/api/profiles/{pid}/experience/{exp_id}", json={"role": "Senior Engineer"})
        assert patch_resp.status_code == 200
        assert patch_resp.json()["role"] == "Senior Engineer"

    def test_delete_experience(self, client):
        pid = _create_profile(client)
        add_resp = client.post(f"/api/profiles/{pid}/experience", json={"company": "X", "role": "Y", "start": "2022"})
        exp_id = add_resp.json()["id"]
        resp = client.delete(f"/api/profiles/{pid}/experience/{exp_id}")
        assert resp.status_code == 204

    def test_add_bullet(self, client):
        pid = _create_profile(client)
        exp_resp = client.post(f"/api/profiles/{pid}/experience", json={"company": "A", "role": "B", "start": "2020"})
        exp_id = exp_resp.json()["id"]
        resp = client.post(f"/api/profiles/{pid}/experience/{exp_id}/bullets", json={"text": "Built cool things"})
        assert resp.status_code == 201
        assert resp.json()["text"] == "Built cool things"

    def test_update_bullet(self, client):
        pid = _create_profile(client)
        exp_resp = client.post(f"/api/profiles/{pid}/experience", json={"company": "A", "role": "B", "start": "2020"})
        exp_id = exp_resp.json()["id"]
        b_resp = client.post(f"/api/profiles/{pid}/experience/{exp_id}/bullets", json={"text": "Original"})
        bid = b_resp.json()["id"]
        patch = client.patch(f"/api/profiles/{pid}/experience/{exp_id}/bullets/{bid}", json={"text": "Updated"})
        assert patch.status_code == 200
        assert patch.json()["text"] == "Updated"

    def test_delete_bullet(self, client):
        pid = _create_profile(client)
        exp_resp = client.post(f"/api/profiles/{pid}/experience", json={"company": "A", "role": "B", "start": "2020"})
        exp_id = exp_resp.json()["id"]
        b_resp = client.post(f"/api/profiles/{pid}/experience/{exp_id}/bullets", json={"text": "Delete me"})
        bid = b_resp.json()["id"]
        resp = client.delete(f"/api/profiles/{pid}/experience/{exp_id}/bullets/{bid}")
        assert resp.status_code == 204


class TestProjectsCRUD:
    def test_add_project(self, client):
        pid = _create_profile(client)
        resp = client.post(f"/api/profiles/{pid}/projects", json={
            "name": "CareerBot", "description": "AI bot", "link": "https://github.com/x", "tech": ["Python", "FastAPI"]
        })
        assert resp.status_code == 201
        body = resp.json()
        assert body["name"] == "CareerBot"
        assert "Python" in body["tech"]

    def test_update_project(self, client):
        pid = _create_profile(client)
        add = client.post(f"/api/profiles/{pid}/projects", json={"name": "Proj", "tech": ["Go"]})
        proj_id = add.json()["id"]
        patch = client.patch(f"/api/profiles/{pid}/projects/{proj_id}", json={"name": "Updated Proj"})
        assert patch.status_code == 200
        assert patch.json()["name"] == "Updated Proj"

    def test_delete_project(self, client):
        pid = _create_profile(client)
        add = client.post(f"/api/profiles/{pid}/projects", json={"name": "ToDelete"})
        proj_id = add.json()["id"]
        resp = client.delete(f"/api/profiles/{pid}/projects/{proj_id}")
        assert resp.status_code == 204


class TestEducationCRUD:
    def test_add_education(self, client):
        pid = _create_profile(client)
        resp = client.post(f"/api/profiles/{pid}/education", json={
            "institution": "Stanford", "degree": "MSc", "field": "AI", "start": "2018", "end": "2020"
        })
        assert resp.status_code == 201
        assert resp.json()["institution"] == "Stanford"

    def test_update_education(self, client):
        pid = _create_profile(client)
        add = client.post(f"/api/profiles/{pid}/education", json={"institution": "Oxford", "degree": "PhD"})
        edu_id = add.json()["id"]
        patch = client.patch(f"/api/profiles/{pid}/education/{edu_id}", json={"field": "NLP"})
        assert patch.status_code == 200
        assert patch.json()["field"] == "NLP"

    def test_delete_education(self, client):
        pid = _create_profile(client)
        add = client.post(f"/api/profiles/{pid}/education", json={"institution": "Harvard"})
        edu_id = add.json()["id"]
        resp = client.delete(f"/api/profiles/{pid}/education/{edu_id}")
        assert resp.status_code == 204


class TestCertificationsCRUD:
    def test_add_certification(self, client):
        pid = _create_profile(client)
        resp = client.post(f"/api/profiles/{pid}/certifications", json={
            "name": "GCP Professional", "issuer": "Google", "date": "2023-06"
        })
        assert resp.status_code == 201
        assert resp.json()["name"] == "GCP Professional"

    def test_update_certification(self, client):
        pid = _create_profile(client)
        add = client.post(f"/api/profiles/{pid}/certifications", json={"name": "Azure", "issuer": "Microsoft"})
        cert_id = add.json()["id"]
        patch = client.patch(f"/api/profiles/{pid}/certifications/{cert_id}", json={"date": "2024-01"})
        assert patch.status_code == 200
        assert patch.json()["date"] == "2024-01"

    def test_delete_certification(self, client):
        pid = _create_profile(client)
        add = client.post(f"/api/profiles/{pid}/certifications", json={"name": "ToDelete"})
        cert_id = add.json()["id"]
        resp = client.delete(f"/api/profiles/{pid}/certifications/{cert_id}")
        assert resp.status_code == 204
