"""Tests for saved filter presets (Issue #7)."""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))


def _auth(client, username):
    r = client.post(
        "/api/auth/register",
        json={"username": username, "password": "password123", "email": f"{username}@x.com"},
    )
    if r.status_code == 400:
        r = client.post("/api/auth/login", data={"username": username, "password": "password123"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _profile(client, headers):
    data = json.dumps({"full_name": "X", "skills": [{"name": "Python"}]}).encode()
    return client.post(
        "/api/import",
        files={"file": ("p.json", data, "application/json")},
        headers=headers,
    ).json()["profile_id"]


def test_create_saved_filter(client):
    h = _auth(client, "sf_creator_v1")
    pid = _profile(client, h)
    r = client.post(
        f"/api/profiles/{pid}/saved-filters",
        json={"name": "Senior Python", "filters": {"min_years": 5}, "sort": "best_match"},
        headers=h,
    )
    assert r.status_code == 201
    body = r.json()
    assert body["name"] == "Senior Python"
    assert body["filters"] == {"min_years": 5}
    assert body["sort"] == "best_match"
    assert "id" in body


def test_list_saved_filters_isolated_per_user(client):
    h_a = _auth(client, "sf_iso_a_v1")
    h_b = _auth(client, "sf_iso_b_v1")
    pid = _profile(client, h_a)
    client.post(
        f"/api/profiles/{pid}/saved-filters",
        json={"name": "Mine", "filters": {}, "sort": "best_match"},
        headers=h_a,
    )
    mine = client.get(f"/api/profiles/{pid}/saved-filters", headers=h_a).json()
    theirs = client.get(f"/api/profiles/{pid}/saved-filters", headers=h_b).json()
    assert any(f["name"] == "Mine" for f in mine)
    assert all(f["name"] != "Mine" for f in theirs)


def test_delete_saved_filter(client):
    h = _auth(client, "sf_del_v1")
    pid = _profile(client, h)
    r = client.post(
        f"/api/profiles/{pid}/saved-filters",
        json={"name": "X", "filters": {}, "sort": "best_match"},
        headers=h,
    )
    sf_id = r.json()["id"]
    d = client.delete(f"/api/profiles/{pid}/saved-filters/{sf_id}", headers=h)
    assert d.status_code == 204
    after = client.get(f"/api/profiles/{pid}/saved-filters", headers=h).json()
    assert all(f["id"] != sf_id for f in after)


def test_other_user_cannot_delete(client):
    h_a = _auth(client, "sf_del_a_v1")
    h_b = _auth(client, "sf_del_b_v1")
    pid = _profile(client, h_a)
    r = client.post(
        f"/api/profiles/{pid}/saved-filters",
        json={"name": "Private", "filters": {}, "sort": "best_match"},
        headers=h_a,
    )
    sf_id = r.json()["id"]
    d = client.delete(f"/api/profiles/{pid}/saved-filters/{sf_id}", headers=h_b)
    assert d.status_code == 404


def test_saved_filter_requires_auth(client):
    h = _auth(client, "sf_noauth_v1")
    pid = _profile(client, h)
    r = client.get(f"/api/profiles/{pid}/saved-filters")
    assert r.status_code == 401


def test_saved_filter_persists_filters_dict(client):
    h = _auth(client, "sf_filters_v1")
    pid = _profile(client, h)
    client.post(
        f"/api/profiles/{pid}/saved-filters",
        json={
            "name": "Complex",
            "filters": {
                "min_years": 3, "max_years": 8,
                "date_posted": "last_7d", "min_match_score": 70,
                "job_type": "remote,full-time",
                "min_salary": 100000, "max_salary": 200000,
                "sort": "recent",
            },
            "sort": "recent",
        },
        headers=h,
    )
    listed = client.get(f"/api/profiles/{pid}/saved-filters", headers=h).json()
    assert len(listed) == 1
    assert listed[0]["filters"]["min_years"] == 3
    assert listed[0]["filters"]["job_type"] == "remote,full-time"
    assert listed[0]["sort"] == "recent"


def test_edit_saved_filter_renames(client):
    h = _auth(client, "sf_edit_v1")
    pid = _profile(client, h)
    r = client.post(
        f"/api/profiles/{pid}/saved-filters",
        json={"name": "OldName", "filters": {}, "sort": "best_match"},
        headers=h,
    )
    sf_id = r.json()["id"]
    patch = client.patch(
        f"/api/profiles/{pid}/saved-filters/{sf_id}",
        json={"name": "NewName"},
        headers=h,
    )
    assert patch.status_code == 200
    assert patch.json()["name"] == "NewName"
    listed = client.get(f"/api/profiles/{pid}/saved-filters", headers=h).json()
    assert listed[0]["name"] == "NewName"


def test_edit_saved_filter_updates_filters_and_sort(client):
    h = _auth(client, "sf_edit_v2")
    pid = _profile(client, h)
    r = client.post(
        f"/api/profiles/{pid}/saved-filters",
        json={"name": "X", "filters": {"min_years": 1}, "sort": "best_match"},
        headers=h,
    )
    sf_id = r.json()["id"]
    patch = client.patch(
        f"/api/profiles/{pid}/saved-filters/{sf_id}",
        json={"filters": {"min_years": 5, "min_match_score": 80}, "sort": "recent"},
        headers=h,
    )
    assert patch.status_code == 200
    body = patch.json()
    assert body["filters"]["min_years"] == 5
    assert body["filters"]["min_match_score"] == 80
    assert body["sort"] == "recent"


def test_edit_other_users_filter_returns_404(client):
    h_a = _auth(client, "sf_edit_a_v1")
    h_b = _auth(client, "sf_edit_b_v1")
    pid = _profile(client, h_a)
    r = client.post(
        f"/api/profiles/{pid}/saved-filters",
        json={"name": "Mine", "filters": {}, "sort": "best_match"},
        headers=h_a,
    )
    sf_id = r.json()["id"]
    patch = client.patch(
        f"/api/profiles/{pid}/saved-filters/{sf_id}",
        json={"name": "Stolen"},
        headers=h_b,
    )
    assert patch.status_code == 404


def test_edit_saved_filter_requires_auth(client):
    h = _auth(client, "sf_edit_noauth_v1")
    pid = _profile(client, h)
    r = client.post(
        f"/api/profiles/{pid}/saved-filters",
        json={"name": "X", "filters": {}, "sort": "best_match"},
        headers=h,
    )
    sf_id = r.json()["id"]
    patch = client.patch(
        f"/api/profiles/{pid}/saved-filters/{sf_id}",
        json={"name": "X"},
    )
    assert patch.status_code == 401
