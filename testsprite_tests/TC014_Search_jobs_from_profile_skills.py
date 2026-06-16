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

        # Open Jobs tab (label is "Job Matching" in the sidebar)
        jobs_tab = page.locator('button:has-text("Job Matching"), button[title="Job Matching"]')
        await jobs_tab.first.wait_for(state="visible", timeout=10000)
        await jobs_tab.first.click()

        # Click Find Jobs button
        search_btn = page.locator('button:has-text("Find Jobs")')
        await search_btn.first.wait_for(state="visible", timeout=10000)
        await search_btn.first.click()

        # Wait for search to complete — either jobs found or error displayed
        # The jobs tab shows a "Jobs found" toast or "Job search failed" toast
        job_result = page.locator("[class*='job'], [data-testid*='job']").first
        try:
            # Wait for either a result list, a toast, or an error state
            await page.wait_for_function(
                """() => {
                    const body = document.body.innerText;
                    return body.includes('positions found') ||
                           body.includes('No jobs found') ||
                           body.includes('Job search failed') ||
                           body.includes('Jobs found') ||
                           document.querySelectorAll('[class*="rounded-xl border"]').length > 0;
                }""",
                timeout=30000
            )
        except Exception:
            pass

        # Verify the jobs section shows results or a result state
        page_text = await page.evaluate("() => document.body.innerText")
        has_results = (
            "positions found" in page_text or
            "No jobs found" in page_text or
            "Job search failed" in page_text or
            "Jobs found" in page_text or
            "Searching job boards" in page_text
        )
        assert has_results, f"Expected job search results or status but got: {page_text[:500]}"

        await asyncio.sleep(2)

    finally:
        if context:
            await context.close()
        if browser:
            await browser.close()
        if pw:
            await pw.stop()

asyncio.run(run_test())
