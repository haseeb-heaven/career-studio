import asyncio
from playwright import async_api
from playwright.async_api import expect

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

        # Click Continue as guest
        elem = page.get_by_role("button", name="Continue as guest (no account)", exact=True)
        await elem.click(timeout=10000)

        # Verify the upload or workspace area is displayed
        # Check for "Drag & drop your resume here" text or the upload container
        await expect(page.get_by_text("Drag & drop your resume here", exact=False)).to_be_visible(timeout=15000)

        # Also verify the "or click to browse files" text is accessible
        browse_text = page.get_by_text("or click to browse files", exact=False)
        await browse_text.wait_for(state="visible", timeout=10000)
        await asyncio.sleep(1)

    finally:
        if context:
            await context.close()
        if browser:
            await browser.close()
        if pw:
            await pw.stop()

asyncio.run(run_test())
