import time
import requests

def test_post_api_auth_register_valid_user():
    base_url = "http://localhost:8000"
    url = f"{base_url}/api/auth/register"

    unique_suffix = str(int(time.time()))[-6:]
    payload = {
        "username": f"testuser-tc001-{unique_suffix}",
        "password": "ValidPass123!",
        "email": f"testuser-tc001-{unique_suffix}@example.com",
    }

    response = requests.post(url, json=payload, timeout=30)
    assert response.status_code in (200, 201), f"Expected 200/201, got {response.status_code}: {response.text}"

    data = response.json()
    assert "access_token" in data, f"access_token not in response: {data}"
    assert "token_type" in data, f"token_type not in response: {data}"
    assert "user_id" in data, f"user_id not in response: {data}"
    assert "username" in data, f"username not in response: {data}"
    assert data["username"] == payload["username"], f"Returned username mismatch: {data}"

test_post_api_auth_register_valid_user()
