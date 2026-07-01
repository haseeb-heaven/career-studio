"""Tests for activity log severity levels and the /logs level filter."""
import json


def _get_auth_headers(client, username: str = "logs_level_user") -> dict:
    resp = client.post(
        "/api/auth/register",
        json={"username": username, "password": "password123", "email": f"{username}@test.local"},
    )
    if resp.status_code == 400:
        resp = client.post("/api/auth/login", data={"username": username, "password": "password123"})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _create_profile(client, headers: dict, skills=None) -> int:
    data = json.dumps({
        "full_name": "Logs Level Test",
        "email": "logs_level@example.com",
        "summary": "Backend engineer.",
        "skills": skills or [{"name": "Python", "years": 5}],
    }).encode()
    resp = client.post("/api/import", files={"file": ("p.json", data, "application/json")}, headers=headers)
    assert resp.status_code == 201
    return resp.json()["profile_id"]


class TestLogActivityPersistsLevel:
    def test_default_level_is_info(self, client):
        import services.activity as activity
        activity.log_activity("patch", "did a thing")
        resp = client.get("/api/logs")
        assert resp.status_code == 200
        entries = [e for e in resp.json() if e["action"] == "patch" and e["detail"] == "did a thing"]
        assert entries and entries[0]["severity"] == "info"

    def test_explicit_warning_level_persists(self, client):
        import services.activity as activity
        activity.log_activity("jobs_search", "found=0/0", level="warning")
        resp = client.get("/api/logs")
        entries = [e for e in resp.json() if e["action"] == "jobs_search" and e["detail"] == "found=0/0"]
        assert entries and entries[0]["severity"] == "warning"

    def test_invalid_level_falls_back_to_info(self, client):
        import services.activity as activity
        activity.log_activity("patch", "bogus level test", level="not-a-real-level")
        resp = client.get("/api/logs")
        entries = [e for e in resp.json() if e["action"] == "patch" and e["detail"] == "bogus level test"]
        assert entries and entries[0]["severity"] == "info"


class TestLogsLevelFilter:
    def test_filter_by_level_returns_only_matching(self, client):
        import services.activity as activity
        activity.log_activity("analyze", "info entry", level="info")
        activity.log_activity("error", "error entry", level="error")

        resp = client.get("/api/logs", params={"level": "error"})
        assert resp.status_code == 200
        body = resp.json()
        assert len(body) > 0
        assert all(e["severity"] == "error" for e in body)
        assert any(e["detail"] == "error entry" for e in body)
        assert not any(e["detail"] == "info entry" for e in body)


class TestJobsSearchZeroResultsLogsWarning:
    def test_zero_results_logged_as_warning_with_cause(self, client, monkeypatch):
        headers = _get_auth_headers(client)
        pid = _create_profile(client, headers, skills=[{"name": "Cobol", "years": 20}])

        import routers.jobs_router as jr
        # Force every external fetcher to a no-op so the search reliably
        # returns zero matches regardless of network availability.
        for attr in dir(jr):
            if attr.startswith("_fetch_"):
                monkeypatch.setattr(jr, attr, lambda *a, **kw: [])

        resp = client.get(
            f"/api/profiles/{pid}/jobs",
            params={"job_title": "Extremely Unlikely Job Title Zzyzx", "min_match_score": 99},
            headers=headers,
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["total"] == 0

        logs = client.get("/api/logs", params={"action": "jobs_search", "level": "warning"}).json()
        assert any("found=0/0" in e["detail"] for e in logs)
