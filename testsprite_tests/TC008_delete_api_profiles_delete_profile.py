import requests

BASE_URL = "http://localhost:8000"
USERNAME = "haseeb-heaven"
PASSWORD = "123456"
TIMEOUT = 30


def get_jwt_token(username, password):
    url = f"{BASE_URL}/api/auth/login"
    data = {
        "username": username,
        "password": password
    }
    resp = requests.post(url, data=data, timeout=TIMEOUT)
    assert resp.status_code == 200, f"Login failed: {resp.status_code}, {resp.text}"
    json_resp = resp.json()
    token = json_resp.get("access_token")
    assert token, "No access_token in login response"
    return token


def test_delete_api_profiles_delete_profile():
    token = get_jwt_token(USERNAME, PASSWORD)
    headers = {"Accept": "application/json", "Authorization": f"Bearer {token}"}

    # Step 1: List profiles to find an existing profile or create one if none exists
    resp_list = requests.get(f"{BASE_URL}/api/profiles", headers=headers, timeout=TIMEOUT)
    assert resp_list.status_code == 200, f"Failed to list profiles: {resp_list.status_code}, {resp_list.text}"
    profiles = resp_list.json()

    profile_id = None
    created_profile = False

    # If no profiles exist, create one by uploading a minimal resume file to /api/import (no auth required)
    if not profiles:
        files = {
            'file': ('test_resume.json', b'{"name":"Test User"}', 'application/json')
        }
        resp_import = requests.post(f"{BASE_URL}/api/import", files=files, timeout=TIMEOUT)
        assert resp_import.status_code == 201, f"Failed to import profile: {resp_import.status_code}, {resp_import.text}"
        profile_id = resp_import.json().get("profile_id")
        assert profile_id, "No profile_id returned from import"
        created_profile = True
    else:
        profile_id = profiles[0].get("id")

    try:
        # Step 2: Delete the profile
        resp_delete = requests.delete(f"{BASE_URL}/api/profiles/{profile_id}", headers=headers, timeout=TIMEOUT)
        assert resp_delete.status_code == 204, f"Expected 204 No Content on delete, got {resp_delete.status_code}, {resp_delete.text}"

        # Step 3: Verify profile deletion by attempting to GET it again and expecting 404
        resp_get = requests.get(f"{BASE_URL}/api/profiles/{profile_id}", headers=headers, timeout=TIMEOUT)
        assert resp_get.status_code == 404, f"Expected 404 Not Found for deleted profile, got {resp_get.status_code}, {resp_get.text}"
    finally:
        # If profile was just created for test and not deleted due to failure, clean up by deleting it
        if created_profile:
            # Try to delete without auth since we just created it anonymously
            try:
                requests.delete(f"{BASE_URL}/api/profiles/{profile_id}", headers=headers, timeout=TIMEOUT)
            except Exception:
                pass


test_delete_api_profiles_delete_profile()
