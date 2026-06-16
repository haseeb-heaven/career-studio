import asyncio
import os
import time
import httpx
from playwright import async_api
from playwright.async_api import expect

BASE_URL = "http://localhost:8000"
FIXTURE = os.path.abspath("./fixtures/sample_resume.json")


async def run_test():
    pw = None
    browser = None
    context = None

    unique_suffix = str(int(time.time()))[-6:]
    test_username = f"tc006-{unique_suffix}"
    test_password = "TestPass123!"

    # Step 1: Register user and create a profile via API so the saved list is non-empty
    with httpx.Client(base_url=BASE_URL, timeout=15) as client:
        reg = client.post("/api/auth/register", json={
            "username": test_username,
            "password": test_password,
        })
        assert reg.status_code in (200, 201, 400), f"Register failed: {reg.text}"

        login_resp = client.post("/api/auth/login", data={
            "username": test_username,
            "password": test_password,
        })
        assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
        token = login_resp.json()["access_token"]

        # Import a profile so the list is non-empty
        with open(FIXTURE, "rb") as f:
            import_resp = client.post(
                "/api/import",
                files={"file": ("sample_resume.json", f, "application/json")},
                headers={"Authorization": f"Bearer {token}"},
            )
        assert import_resp.status_code in (200, 201), f"Import failed: {import_resp.text}"

    try:
        pw = await async_api.async_playwright().start()
        browser = await pw.chromium.launch(
            headless=True,
            args=[
                "--window-size=1280,720",
                "--disable-dev-shm-usage",
                "--no-sandbox",
            ],
        )
        context = await browser.new_context()
        context.set_default_timeout(15000)
        page = await context.new_page()

        await page.goto("http://localhost:5173")
        try:
            await page.wait_for_load_state("domcontentloaded", timeout=5000)
        except Exception:
            pass

        # Step 2: Log in via the UI
        username_input = page.get_by_placeholder("Enter username", exact=True)
        await username_input.wait_for(state="visible", timeout=10000)
        await username_input.fill(test_username)

        password_input = page.get_by_placeholder("Password", exact=True)
        await password_input.fill(test_password)

        # Use .last because "Sign In" appears in both the tab button and submit button
        sign_in_btn = page.get_by_role("button", name="Sign In", exact=True).last
        await sign_in_btn.click(timeout=10000)

        # Step 3: After login, click "Open Saved Profile" on the upload screen
        open_btn = page.locator('button:has-text("Open Saved Profile")')
        await open_btn.wait_for(state="visible", timeout=10000)
        await open_btn.click()

        # Step 4: The saved profiles list should now appear
        # Look for an "Open →" button or a profile card in the list
        open_profile_btn = page.get_by_role("button", name="Open →", exact=True).first
        await open_profile_btn.wait_for(state="visible", timeout=10000)
        await open_profile_btn.click()

        # Step 5: Verify the ProfileEditor loaded (Contact tab button should be visible)
        contact_tab = page.locator('button:has-text("Contact")')
        await contact_tab.first.wait_for(state="visible", timeout=15000)
        await asyncio.sleep(1)

    finally:
        if context:
            await context.close()
        if browser:
            await browser.close()
        if pw:
            await pw.stop()


asyncio.run(run_test())
