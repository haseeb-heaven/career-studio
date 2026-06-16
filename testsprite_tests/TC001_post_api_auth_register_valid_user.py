import requests
from requests.auth import HTTPBasicAuth

def test_post_api_auth_register_valid_user():
    base_url = "http://localhost:8000"
    url = f"{base_url}/api/auth/register"
    auth_username = "haseeb-heaven"
    auth_password = "123456"
    headers = {
        "Content-Type": "application/json"
    }
    payload = {
        "username": "testuser_valid_tc001",
        "password": "ValidPass123!",
        "email": "testuser_valid_tc001@example.com"
    }

    try:
        # Although registration does not require auth, instructions specify basic token auth, so we include it.
        response = requests.post(
            url,
            json=payload,
            headers=headers,
            auth=HTTPBasicAuth(auth_username, auth_password),
            timeout=30
        )

        assert response.status_code == 201, f"Expected 201, got {response.status_code}"
        data = response.json()
        assert "access_token" in data, "access_token not in response"
        assert "token_type" in data, "token_type not in response"
        assert "user_id" in data, "user_id not in response"
        assert "username" in data, "username not in response"
        assert data["username"] == payload["username"], "Returned username mismatch"

    except requests.RequestException as e:
        assert False, f"Request failed: {e}"

test_post_api_auth_register_valid_user()