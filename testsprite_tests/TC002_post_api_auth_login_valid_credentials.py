import requests
from requests.auth import HTTPBasicAuth

BASE_URL = "http://localhost:8000"
TIMEOUT = 30

def test_post_api_auth_login_valid_credentials():
    url = f"{BASE_URL}/api/auth/login"
    auth = HTTPBasicAuth("haseeb-heaven", "123456")
    # According to PRD, the login expects form data with username and password fields
    payload = {
        "username": "haseeb-heaven",
        "password": "123456"
    }
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }
    try:
        response = requests.post(url, data=payload, headers=headers, timeout=TIMEOUT)
    except requests.RequestException as e:
        assert False, f"Request failed: {e}"

    assert response.status_code == 200, f"Expected status code 200, got {response.status_code}"
    json_data = None
    try:
        json_data = response.json()
    except ValueError:
        assert False, "Response is not valid JSON"

    assert "access_token" in json_data, "access_token missing in response"
    assert "token_type" in json_data, "token_type missing in response"
    assert "user_id" in json_data, "user_id missing in response"
    assert "username" in json_data, "username missing in response"
    assert json_data["username"] == "haseeb-heaven", "Response username does not match login username"

test_post_api_auth_login_valid_credentials()