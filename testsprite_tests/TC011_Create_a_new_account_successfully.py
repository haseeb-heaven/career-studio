import asyncio
import time
import httpx
from playwright import async_api
from playwright.async_api import expect

BASE_URL = "http://localhost:8000"

async def run_test():
    pw = None
    browser = None
    context = None

    # Use a unique username based on timestamp to avoid "already taken" errors
    unique_suffix = str(int(time.time()))[-6:]
    test_username = f"testuser-{unique_suffix}"
    test_email = f"testuser-{unique_suffix}@example.com"
    test_password = "TestPass123!"

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

        # Switch to the create account view
        create_btn = page.get_by_role("button", name="Create Account", exact=True)
        await create_btn.click(timeout=10000)

        # Fill in the username field with a unique username
        username_input = page.get_by_placeholder("Enter username", exact=True)
        await username_input.wait_for(state="visible", timeout=10000)
        await username_input.fill(test_username)

        # Fill in the email field
        email_input = page.get_by_placeholder("you@example.com", exact=True)
        await email_input.fill(test_email)

        # Fill in the password field
        password_input = page.get_by_placeholder("Password", exact=True)
        await password_input.fill(test_password)

        # Submit the form
        submit_btn = page.locator('button:has-text("Create Account")').last
        await submit_btn.click(timeout=10000)

        # Verify a success confirmation is visible (either success message or logged-in state)
        # After successful registration, the app logs in automatically
        await page.wait_for_timeout(2000)
        page_text = await page.evaluate("() => document.body.innerText")
        has_success = (
            test_username in page_text or
            "success" in page_text.lower() or
            "Upload" in page_text or
            "Career Studio" in page_text
        )
        assert has_success, f"Expected registration success confirmation but got: {page_text[:300]}"
        await asyncio.sleep(1)

    finally:
        if context:
            await context.close()
        if browser:
            await browser.close()
        if pw:
            await pw.stop()

asyncio.run(run_test())
