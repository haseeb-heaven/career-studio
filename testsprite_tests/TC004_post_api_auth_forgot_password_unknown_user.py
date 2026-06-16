import requests
from requests.auth import HTTPBasicAuth

BASE_URL = "http://localhost:8000"

def test_post_api_auth_forgot_password_unknown_user():
    url = f"{BASE_URL}/api/auth/forgot-password"
    unknown_username = "user_does_not_exist_12345"
    headers = {
        "Content-Type": "application/json"
    }
    auth = HTTPBasicAuth("haseeb-heaven", "123456")
    payload = {
        "username": unknown_username
    }
    try:
        response = requests.post(url, json=payload, headers=headers, auth=auth, timeout=30)
    except requests.RequestException as e:
        assert False, f"Request failed: {e}"
    assert response.status_code == 404, f"Expected status code 404, got {response.status_code}"
    # Response should indicate user not found
    try:
        json_resp = response.json()
    except ValueError:
        assert False, "Response is not valid JSON"
    # The 404 response content is likely a string message or object, accept any content
    # but verify that it relates to user not found (if message is provided)
    if isinstance(json_resp, dict):
        msg = json_resp.get("detail") or json_resp.get("message") or ""
        assert "not found" in msg.lower() or "user" in msg.lower(), f"Unexpected 404 response content: {json_resp}"

test_post_api_auth_forgot_password_unknown_user()