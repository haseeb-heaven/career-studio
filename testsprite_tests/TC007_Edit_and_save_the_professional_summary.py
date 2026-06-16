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

        # Continue as guest and upload resume
        elem = page.get_by_role("button", name="Continue as guest (no account)", exact=True)
        await elem.click(timeout=10000)

        file_input = page.locator('input[type="file"]').first
        await file_input.wait_for(state="attached", timeout=10000)
        await file_input.set_input_files(FIXTURE)

        # Wait for profile editor to load
        await page.wait_for_timeout(3000)

        # Open Summary tab (sidebar button has icon+label or title="Summary")
        summary_tab = page.locator('button[title="Summary"], button:has-text("Summary")')
        await summary_tab.first.wait_for(state="visible", timeout=10000)
        await summary_tab.first.click()

        # Edit the summary textarea
        summary_area = page.locator("textarea").first
        await summary_area.wait_for(state="visible", timeout=10000)
        await summary_area.fill("Experienced software engineer with 8+ years building scalable backend systems.")

        # Save the summary
        save_btn = page.get_by_role("button", name="Save Summary", exact=True)
        await save_btn.click(timeout=10000)

        # Verify success notification is visible
        await expect(page.get_by_text("Summary saved", exact=False)).to_be_visible(timeout=15000)

        # Verify the character count or summary text is updated
        summary_content = await summary_area.input_value()
        assert "8+ years" in summary_content, f"Summary text not updated: {summary_content}"

        await asyncio.sleep(2)

    finally:
        if context:
            await context.close()
        if browser:
            await browser.close()
        if pw:
            await pw.stop()

asyncio.run(run_test())
