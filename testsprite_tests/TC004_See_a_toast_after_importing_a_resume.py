import asyncio
import os
from playwright import async_api
from playwright.async_api import expect

FIXTURE = os.path.abspath("./fixtures/sample_resume.json")

async def run_test():
    pw = None
    browser = None
    context = None

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

        await page.goto("http://localhost:5173")
        try:
            await page.wait_for_load_state("domcontentloaded", timeout=5000)
        except Exception:
            pass

        # Continue as guest
        elem = page.get_by_role("button", name="Continue as guest (no account)", exact=True)
        await elem.click(timeout=10000)

        # Upload resume via file input
        file_input = page.locator('input[type="file"]').first
        await file_input.wait_for(state="attached", timeout=10000)
        await file_input.set_input_files(FIXTURE)

        # Verify import success toast is displayed
        await expect(page.get_by_text("Resume imported", exact=False)).to_be_visible(timeout=15000)

        # Verify the toast dismisses automatically (within 8 seconds)
        await expect(page.get_by_text("Resume imported", exact=False)).not_to_be_visible(timeout=8000)
        await asyncio.sleep(1)

    finally:
        if context:
            await context.close()
        if browser:
            await browser.close()
        if pw:
            await pw.stop()

asyncio.run(run_test())
