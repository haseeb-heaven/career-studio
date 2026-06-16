import requests
from requests.auth import HTTPBasicAuth

BASE_URL = "http://localhost:8000"
USERNAME = "haseeb-heaven"
PASSWORD = "123456"
TIMEOUT = 30

def test_patch_api_profiles_update_top_level_fields():
    # Authenticate to get JWT token
    login_url = f"{BASE_URL}/api/auth/login"
    login_data = {
        "username": USERNAME,
        "password": PASSWORD
    }
    login_resp = requests.post(login_url, data=login_data, timeout=TIMEOUT)
    assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
    login_json = login_resp.json()
    access_token = login_json.get("access_token")
    token_type = login_json.get("token_type")
    assert access_token and token_type, "Missing access token or token type"

    headers = {
        "Authorization": f"{token_type} {access_token}",
        "Content-Type": "application/json"
    }

    # Get list of profiles to pick a profile_id for update
    profiles_url = f"{BASE_URL}/api/profiles"
    profiles_resp = requests.get(profiles_url, headers=headers, timeout=TIMEOUT)
    assert profiles_resp.status_code == 200, f"Failed getting profiles: {profiles_resp.text}"
    profiles = profiles_resp.json()
    assert isinstance(profiles, list), "Profiles response is not a list"

    # If no profile, create one via import (using empty minimal resume as fallback)
    profile_id = None
    created_profile_id = None
    if not profiles:
        # Create a minimal profile by importing a minimal supported resume file (JSON format empty)
        import_url = f"{BASE_URL}/api/import"
        files = {
            "file": ("minimal.json", b"{}", "application/json")
        }
        import_resp = requests.post(import_url, files=files, timeout=TIMEOUT)
        assert import_resp.status_code == 201, f"Failed to create profile via import: {import_resp.text}"
        import_json = import_resp.json()
        created_profile_id = import_json.get("profile_id")
        assert created_profile_id, "Import response missing profile_id"
        profile_id = created_profile_id
    else:
        profile_id = profiles[0]["id"]

    patch_url = f"{BASE_URL}/api/profiles/{profile_id}"

    # Partial data to update top-level fields (some valid partial fields)
    patch_data = {
        "full_name": "Updated Test User",
        "location": "New York, NY",
        "summary": "Updated summary info"
    }

    import json

    try:
        patch_resp = requests.patch(
            patch_url,
            headers=headers,
            json=patch_data,
            timeout=TIMEOUT
        )
        assert patch_resp.status_code == 200, f"Patch failed: {patch_resp.text}"
        patch_json = patch_resp.json()
        assert patch_json.get("id") == profile_id, "Returned profile id mismatch"
        assert patch_json.get("full_name") == patch_data["full_name"], "Full name not updated correctly"

        # Verify persisted data with GET
        get_resp = requests.get(patch_url, headers=headers, timeout=TIMEOUT)
        assert get_resp.status_code == 200, f"Failed GET after patch: {get_resp.text}"
        get_json = get_resp.json()
        assert get_json.get("full_name") == patch_data["full_name"], "Persisted full_name mismatch"
        assert get_json.get("location") == patch_data["location"], "Persisted location mismatch"
        assert get_json.get("summary") == patch_data["summary"], "Persisted summary mismatch"

    finally:
        if created_profile_id:
            # Cleanup: delete the created profile
            del_url = f"{BASE_URL}/api/profiles/{created_profile_id}"
            del_resp = requests.delete(del_url, headers=headers, timeout=TIMEOUT)
            # Allow 204 or 404 (in case already deleted)
            assert del_resp.status_code in (204, 404), f"Failed to delete profile: {del_resp.text}"

test_patch_api_profiles_update_top_level_fields()
