import requests
from requests.auth import HTTPBasicAuth

BASE_URL = "http://localhost:8000"
USERNAME = "haseeb-heaven"
PASSWORD = "123456"
TIMEOUT = 30

def test_get_api_profiles_export_supported_format():
    # Authenticate using basic token (simulate login to get JWT token)
    login_url = f"{BASE_URL}/api/auth/login"
    login_data = {"username": USERNAME, "password": PASSWORD}
    
    login_resp = requests.post(login_url, data=login_data, timeout=TIMEOUT)
    assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
    auth_json = login_resp.json()
    access_token = auth_json.get("access_token")
    assert access_token, "Missing access_token in login response"

    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    profile_id = None
    created_profile_id = None

    try:
        # List profiles to get a valid profile_id
        profiles_url = f"{BASE_URL}/api/profiles"
        profiles_resp = requests.get(profiles_url, headers=headers, timeout=TIMEOUT)
        assert profiles_resp.status_code == 200, f"Get profiles failed: {profiles_resp.text}"
        profiles = profiles_resp.json()
        if profiles and isinstance(profiles, list):
            profile_id = profiles[0]["id"]
        else:
            profile_id = None
        
        # If no profile found, create one by uploading a minimal resume file (JSON)
        if not profile_id:
            import_url = f"{BASE_URL}/api/import"
            resume_data = {
                "file": (
                    "resume.json",
                    b'{"basics":{"name":"Test User","email":"test@example.com"}}',
                    "application/json"
                )
            }
            import_resp = requests.post(import_url, files=resume_data, timeout=TIMEOUT)
            assert import_resp.status_code == 201, f"Import resume failed: {import_resp.text}"
            import_json = import_resp.json()
            created_profile_id = import_json.get("profile_id")
            assert created_profile_id, "Profile ID missing in import response"
            profile_id = created_profile_id

        # Supported export format (using "pdf" as common supported format)
        export_fmt = "pdf"
        export_url = f"{BASE_URL}/api/profiles/{profile_id}/export/{export_fmt}"

        export_resp = requests.get(export_url, headers=headers, timeout=TIMEOUT)
        assert export_resp.status_code == 200, f"Export failed: {export_resp.text}"

        # Validate response is binary file download (Content-Type roughly pdf or octet-stream)
        content_type = export_resp.headers.get("Content-Type", "")
        assert content_type in [
            "application/pdf",
            "application/octet-stream",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/json",
            "text/csv",
            "application/xml",
            "text/html",
            "application/x-tex"
        ], f"Unexpected content type: {content_type}"

        # Basic check that content is not empty and binary (bytes)
        content = export_resp.content
        assert content and isinstance(content, bytes), "Exported content is empty or invalid"

    finally:
        # Cleanup created profile if any
        if created_profile_id:
            delete_url = f"{BASE_URL}/api/profiles/{created_profile_id}"
            del_resp = requests.delete(delete_url, headers=headers, timeout=TIMEOUT)
            assert del_resp.status_code == 204, f"Cleanup delete profile failed: {del_resp.text}"

test_get_api_profiles_export_supported_format()