import asyncio
import re
import httpx
from playwright import async_api
from playwright.async_api import expect

LOGIN_USER = "testuser"
LOGIN_PASSWORD = "TestPass123!"
BASE_URL = "http://localhost:8000"

async def run_test():
    pw = None
    browser = None
    context = None

    # Ensure the test user exists by registering (ignore conflict if already exists)
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=10) as client:
        await client.post("/api/auth/register", json={
            "username": LOGIN_USER,
            "email": f"{LOGIN_USER}@example.com",
            "password": LOGIN_PASSWORD,
        })
        # Request a real reset token
        resp = await client.post("/api/auth/forgot-password", json={"username": LOGIN_USER})
        resp.raise_for_status()
        data = resp.json()
        dev_reset_url = data.get("dev_reset_url", "")
        assert dev_reset_url, f"No dev_reset_url in response: {data}"

    try:
        pw = await async_api.async_playwright().start()
        browser = await pw.chromium.launch(
            headless=True,
            args=[
                "--window-size=1280,720",
                "--disable-dev-shm-usage",
                "--ipc=host",
                "--single-process"
            ],
        )
        context = await browser.new_context()
        context.set_default_timeout(15000)
        page = await context.new_page()

        # Navigate directly to the reset URL (contains a real JWT)
        await page.goto(dev_reset_url)
        try:
            await page.wait_for_load_state("domcontentloaded", timeout=5000)
        except Exception:
            pass

        # Fill new password and submit
        password_field = page.get_by_placeholder("Password", exact=True)
        await password_field.wait_for(state="visible", timeout=10000)
        await password_field.fill("NewValidP@ssw0rd123")

        reset_btn = page.get_by_role("button", name="Reset Password", exact=True)
        await reset_btn.click(timeout=10000)

        # Verify success — backend returns "Password updated successfully"
        await expect(page.get_by_text("Password updated successfully", exact=False)).to_be_visible(timeout=15000)
        await asyncio.sleep(2)

    finally:
        if context:
            await context.close()
        if browser:
            await browser.close()
        if pw:
            await pw.stop()

asyncio.run(run_test())
