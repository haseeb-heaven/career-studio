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

        # Continue as guest and upload resume (which has skills)
        elem = page.get_by_role("button", name="Continue as guest (no account)", exact=True)
        await elem.click(timeout=10000)

        file_input = page.locator('input[type="file"]').first
        await file_input.wait_for(state="attached", timeout=10000)
        await file_input.set_input_files(FIXTURE)

        # Wait for profile editor to load
        await page.wait_for_timeout(3000)

        # Open Skills tab
        skills_tab = page.locator('button:has-text("Skills"), button[title="Skills"]')
        await skills_tab.first.wait_for(state="visible", timeout=10000)
        await skills_tab.first.click()

        # Wait for skills list to render
        await page.wait_for_timeout(1000)

        # Find the first "Del" button (to delete first skill)
        del_btn = page.get_by_role("button", name="Del", exact=True).first
        await del_btn.wait_for(state="visible", timeout=10000)

        # Delete the skill
        await del_btn.click(timeout=10000)

        # Verify "Skill removed" toast appears
        await expect(page.get_by_text("Skill removed", exact=False)).to_be_visible(timeout=15000)
        await asyncio.sleep(2)

    finally:
        if context:
            await context.close()
        if browser:
            await browser.close()
        if pw:
            await pw.stop()

asyncio.run(run_test())
