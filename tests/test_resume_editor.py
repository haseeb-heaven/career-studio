"""Tests for the live resume/CV editor: generate, save, suggest, export."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))


def _get_auth_headers(client, username: str = "resume_editor_user") -> dict:
    resp = client.post(
        "/api/auth/register",
        json={"username": username, "password": "password123", "email": f"{username}@test.local"},
    )
    if resp.status_code == 400:
        resp = client.post("/api/auth/login", data={"username": username, "password": "password123"})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _create_profile(client, headers: dict) -> int:
    data = json.dumps({
        "full_name": "Resume Editor Test",
        "email": "ret@example.com",
        "summary": "Backend engineer.",
        "skills": [{"name": "Python", "years": 5}],
        "experience": [{"company": "Acme", "role": "Engineer", "start": "2020"}],
    }).encode()
    resp = client.post("/api/import", files={"file": ("p.json", data, "application/json")}, headers=headers)
    assert resp.status_code == 201
    return resp.json()["profile_id"]


def _mock_complete_complex(monkeypatch, return_value):
    import routers.resume_editor_router as rer
    monkeypatch.setattr(rer, "complete_complex", lambda system, user, user_id=None: return_value)


class TestGenerateDraft:
    def test_generate_creates_draft_from_profile(self, client, monkeypatch):
        headers = _get_auth_headers(client, "resume_gen_user")
        pid = _create_profile(client, headers)
        _mock_complete_complex(monkeypatch, "# Resume Editor Test\n\n## Summary\n- Backend engineer.\n")

        resp = client.post(f"/api/profiles/{pid}/resume-drafts/generate", json={"title": "Draft 1"}, headers=headers)
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["title"] == "Draft 1"
        assert "Backend engineer" in body["content"]
        assert body["id"] > 0

    def test_generate_ai_error_returns_502(self, client, monkeypatch):
        headers = _get_auth_headers(client, "resume_gen_err_user")
        pid = _create_profile(client, headers)
        import routers.resume_editor_router as rer

        def _raise(*a, **kw):
            raise RuntimeError("provider down")
        monkeypatch.setattr(rer, "complete_complex", _raise)

        resp = client.post(f"/api/profiles/{pid}/resume-drafts/generate", json={}, headers=headers)
        assert resp.status_code == 502


class TestListSaveDeleteDraft:
    def test_full_lifecycle(self, client, monkeypatch):
        headers = _get_auth_headers(client, "resume_lifecycle_user")
        pid = _create_profile(client, headers)
        _mock_complete_complex(monkeypatch, "# Resume Editor Test\n\n## Summary\nBackend engineer.\n")

        gen = client.post(f"/api/profiles/{pid}/resume-drafts/generate", json={}, headers=headers).json()
        draft_id = gen["id"]

        listed = client.get(f"/api/profiles/{pid}/resume-drafts", headers=headers)
        assert listed.status_code == 200
        assert any(d["id"] == draft_id for d in listed.json())

        saved = client.put(
            f"/api/profiles/{pid}/resume-drafts/{draft_id}",
            json={"title": "Edited Title", "content": "# Edited\n\nNew content here."},
            headers=headers,
        )
        assert saved.status_code == 200, saved.text
        assert saved.json()["title"] == "Edited Title"
        assert saved.json()["content"] == "# Edited\n\nNew content here."

        # Persisted — a fresh GET reflects the edit, not the AI-generated original
        relisted = client.get(f"/api/profiles/{pid}/resume-drafts", headers=headers).json()
        match = next(d for d in relisted if d["id"] == draft_id)
        assert match["content"] == "# Edited\n\nNew content here."

        deleted = client.delete(f"/api/profiles/{pid}/resume-drafts/{draft_id}", headers=headers)
        assert deleted.status_code == 200
        relisted2 = client.get(f"/api/profiles/{pid}/resume-drafts", headers=headers).json()
        assert not any(d["id"] == draft_id for d in relisted2)

    def test_save_nonexistent_draft_404(self, client):
        headers = _get_auth_headers(client, "resume_404_user")
        pid = _create_profile(client, headers)
        resp = client.put(
            f"/api/profiles/{pid}/resume-drafts/999999",
            json={"content": "x"},
            headers=headers,
        )
        assert resp.status_code == 404


class TestSuggestEdits:
    def test_suggest_returns_suggestion_list(self, client, monkeypatch):
        headers = _get_auth_headers(client, "resume_suggest_user")
        pid = _create_profile(client, headers)
        _mock_complete_complex(monkeypatch, "# Resume\nBackend engineer.\n")
        gen = client.post(f"/api/profiles/{pid}/resume-drafts/generate", json={}, headers=headers).json()
        draft_id = gen["id"]

        import routers.resume_editor_router as rer
        monkeypatch.setattr(
            rer, "complete_complex",
            lambda system, user, user_id=None: json.dumps({
                "suggestions": ["Quantify your impact in the Acme role.", "Use a stronger action verb."]
            }),
        )
        resp = client.post(f"/api/profiles/{pid}/resume-drafts/{draft_id}/suggest", headers=headers)
        assert resp.status_code == 200, resp.text
        suggestions = resp.json()["suggestions"]
        assert len(suggestions) == 2
        assert "Quantify" in suggestions[0]

        # Suggestions are advisory only — draft content must be untouched.
        after = client.get(f"/api/profiles/{pid}/resume-drafts", headers=headers).json()
        match = next(d for d in after if d["id"] == draft_id)
        assert match["content"] == "# Resume\nBackend engineer.\n"


class TestExportDraft:
    def _make_draft(self, client, headers, pid, monkeypatch):
        _mock_complete_complex(
            monkeypatch,
            "# Resume Editor Test\n\n## Summary\n- Backend engineer with 5 years experience.\n\n## Skills\n- Python\n- FastAPI\n",
        )
        return client.post(f"/api/profiles/{pid}/resume-drafts/generate", json={"title": "Export Draft"}, headers=headers).json()["id"]

    def test_export_txt(self, client, monkeypatch):
        headers = _get_auth_headers(client, "resume_export_txt_user")
        pid = _create_profile(client, headers)
        draft_id = self._make_draft(client, headers, pid, monkeypatch)
        resp = client.get(f"/api/profiles/{pid}/resume-drafts/{draft_id}/export/txt", headers=headers)
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/plain")
        assert b"Backend engineer" in resp.content

    def test_export_md(self, client, monkeypatch):
        headers = _get_auth_headers(client, "resume_export_md_user")
        pid = _create_profile(client, headers)
        draft_id = self._make_draft(client, headers, pid, monkeypatch)
        resp = client.get(f"/api/profiles/{pid}/resume-drafts/{draft_id}/export/md", headers=headers)
        assert resp.status_code == 200
        assert b"## Summary" in resp.content

    def test_export_docx(self, client, monkeypatch):
        headers = _get_auth_headers(client, "resume_export_docx_user")
        pid = _create_profile(client, headers)
        draft_id = self._make_draft(client, headers, pid, monkeypatch)
        resp = client.get(f"/api/profiles/{pid}/resume-drafts/{draft_id}/export/docx", headers=headers)
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith(
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        assert len(resp.content) > 100

    def test_export_pdf(self, client, monkeypatch):
        headers = _get_auth_headers(client, "resume_export_pdf_user")
        pid = _create_profile(client, headers)
        draft_id = self._make_draft(client, headers, pid, monkeypatch)
        resp = client.get(f"/api/profiles/{pid}/resume-drafts/{draft_id}/export/pdf", headers=headers)
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/pdf"
        assert resp.content.startswith(b"%PDF")

    def test_export_unsupported_format_400(self, client, monkeypatch):
        headers = _get_auth_headers(client, "resume_export_bad_user")
        pid = _create_profile(client, headers)
        draft_id = self._make_draft(client, headers, pid, monkeypatch)
        resp = client.get(f"/api/profiles/{pid}/resume-drafts/{draft_id}/export/exe", headers=headers)
        assert resp.status_code == 400
