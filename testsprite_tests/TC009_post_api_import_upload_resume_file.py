import requests
from requests.auth import HTTPBasicAuth
import io

def test_post_api_import_upload_resume_file():
    base_url = "http://localhost:8000"
    import_endpoint = f"{base_url}/api/import"
    auth = HTTPBasicAuth("haseeb-heaven", "123456")
    timeout = 30

    # Prepare a simple supported resume file content (PDF format)
    # Minimal valid PDF header content to simulate a file
    pdf_content = b"%PDF-1.4\n% Fake PDF content for testing\n"

    files = {
        'file': ('test_resume.pdf', io.BytesIO(pdf_content), 'application/pdf')
    }

    try:
        response = requests.post(import_endpoint, files=files, auth=auth, timeout=timeout)
    except requests.RequestException as e:
        assert False, f"Request failed: {e}"

    assert response.status_code == 201, f"Expected 201 Created, got {response.status_code}"

    json_resp = None
    try:
        json_resp = response.json()
    except ValueError:
        assert False, "Response is not a valid JSON"

    assert 'profile_id' in json_resp, "'profile_id' not in response JSON"
    assert 'warnings' in json_resp, "'warnings' not in response JSON"
    # profile_id should be string or int (assuming string or int ID)
    profile_id = json_resp['profile_id']
    assert isinstance(profile_id, (str, int)), "profile_id should be string or int"
    # warnings should be a list (possibly empty)
    warnings = json_resp['warnings']
    assert isinstance(warnings, list), "warnings should be a list"

test_post_api_import_upload_resume_file()
