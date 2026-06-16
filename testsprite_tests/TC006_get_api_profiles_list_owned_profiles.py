import requests

def test_get_api_profiles_list_owned_profiles():
    base_url = "http://localhost:8000"
    login_url = f"{base_url}/api/auth/login"
    profiles_url = f"{base_url}/api/profiles"

    # Authenticate and get JWT token
    login_data = {
        "username": "haseeb-heaven",
        "password": "123456"
    }

    try:
        login_response = requests.post(login_url, data=login_data, timeout=30)
        login_response.raise_for_status()
    except requests.exceptions.RequestException as e:
        assert False, f"Login request failed: {e}"

    assert login_response.status_code == 200, f"Login unexpected status code: {login_response.status_code}"

    try:
        token_data = login_response.json()
    except ValueError:
        assert False, "Login response is not valid JSON"

    assert "access_token" in token_data, "Login response missing access_token"
    access_token = token_data["access_token"]

    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {access_token}"
    }

    try:
        response = requests.get(profiles_url, headers=headers, timeout=30)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        assert False, f"Profiles request failed: {e}"

    assert response.status_code == 200, f"Profiles unexpected status code: {response.status_code}"
    try:
        profiles = response.json()
    except ValueError:
        assert False, "Profiles response is not valid JSON"

    assert isinstance(profiles, list), "Response JSON is not a list"
    for profile in profiles:
        assert isinstance(profile, dict), "Profile item is not a dictionary"
        assert "id" in profile, "Profile dictionary missing 'id'"
        assert "full_name" in profile, "Profile dictionary missing 'full_name'"
        # 'email' is optional and may be None, check if present
        assert "email" in profile, "Profile dictionary missing 'email'"


test_get_api_profiles_list_owned_profiles()