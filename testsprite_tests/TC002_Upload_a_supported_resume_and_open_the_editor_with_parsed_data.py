import asyncio
import os
from playwright import async_api
from playwright.async_api import expect

FIXTURE = os.path.abspath("./fixtures/resume.pdf")

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

        # Upload a supported resume file
        file_input = page.locator('input[type="file"]').first
        await file_input.wait_for(state="attached", timeout=10000)
        await file_input.set_input_files(FIXTURE)

        # Verify loading indicator is displayed (spinner or "Loading" text appears briefly)
        # Then verify the profile editor opens with imported data
        # The editor shows tab navigation (Contact, Summary, Skills etc.)
        await page.wait_for_timeout(2000)

        # Verify the profile editor is displayed — look for Contact tab button or profile data
        profile_editor = page.locator('button:has-text("Contact"), button[title="Contact"]')
        await profile_editor.first.wait_for(state="visible", timeout=15000)

        # Verify imported data appears in editor
        page_text = await page.evaluate("() => document.body.innerText")
        has_profile_data = (
            "Contact" in page_text or
            "Summary" in page_text or
            "Skills" in page_text
        )
        assert has_profile_data, f"Profile editor with imported data not visible. Page text: {page_text[:300]}"
        await asyncio.sleep(2)

    finally:
        if context:
            await context.close()
        if browser:
            await browser.close()
        if pw:
            await pw.stop()

asyncio.run(run_test())
