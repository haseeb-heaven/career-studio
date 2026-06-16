import requests

BASE_URL = "http://localhost:8000"
USERNAME = "haseeb-heaven"
PASSWORD = "123456"
TIMEOUT = 30

def test_get_api_auth_me_authenticated_user():
    login_url = f"{BASE_URL}/api/auth/login"
    me_url = f"{BASE_URL}/api/auth/me"

    try:
        # Step 1: Login to get JWT token
        login_response = requests.post(
            login_url,
            data={"username": USERNAME, "password": PASSWORD},
            timeout=TIMEOUT
        )
        assert login_response.status_code == 200, f"Login failed: {login_response.text}"
        login_data = login_response.json()
        assert "access_token" in login_data, "access_token missing in login response"
        assert "token_type" in login_data, "token_type missing in login response"
        assert login_data["token_type"].lower() == "bearer", "token_type is not Bearer"
        token = login_data["access_token"]

        # Step 2: Use Bearer token to get current authenticated user info
        headers = {
            "Authorization": f"Bearer {token}"
        }
        me_response = requests.get(me_url, headers=headers, timeout=TIMEOUT)
        assert me_response.status_code == 200, f"Auth me failed: {me_response.text}"
        me_data = me_response.json()
        # Validate keys in user info response
        assert "user_id" in me_data, "user_id missing in authenticated user data"
        assert "username" in me_data, "username missing in authenticated user data"
        # email can be optional or null, but if present check type
        if "email" in me_data:
            assert isinstance(me_data["email"], (str, type(None))), "email is not string or null"

    except requests.RequestException as e:
        assert False, f"Request failed: {str(e)}"

test_get_api_auth_me_authenticated_user()
