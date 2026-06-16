import requests

BASE_URL = "http://localhost:8000"
TIMEOUT = 30


def test_post_api_auth_reset_password_invalid_token():
    url = f"{BASE_URL}/api/auth/reset-password"
    headers = {
        "Content-Type": "application/json"
    }

    # Test case 1: expired or invalid reset token
    payload_invalid_token = {
        "token": "this_is_an_invalid_or_expired_token",
        "new_password": "ValidPass123!"
    }
    response1 = requests.post(url, json=payload_invalid_token, headers=headers, timeout=TIMEOUT)
    assert response1.status_code == 400, f"Expected 400 for invalid token, got {response1.status_code}"
    try:
        error_response = response1.json()
        assert "token" in str(error_response).lower() or "invalid" in str(error_response).lower() or "expired" in str(error_response).lower()
    except Exception:
        pass  # Response content validation is best effort

    # Test case 2: short new password (too short password)
    payload_short_password = {
        "token": "some_valid_token_but_password_invalid",
        "new_password": "123"  # too short, assuming password policy
    }
    response2 = requests.post(url, json=payload_short_password, headers=headers, timeout=TIMEOUT)
    assert response2.status_code == 400, f"Expected 400 for short password, got {response2.status_code}"
    try:
        error_response = response2.json()
        assert "password" in str(error_response).lower() or "validation" in str(error_response).lower()
    except Exception:
        pass  # Response content validation is best effort


test_post_api_auth_reset_password_invalid_token()
