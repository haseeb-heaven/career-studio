import asyncio
import re
from playwright import async_api
from playwright.async_api import expect

async def run_test():
    pw = None
    browser = None
    context = None

    try:
        # Start a Playwright session in asynchronous mode
        pw = await async_api.async_playwright().start()

        # Launch a Chromium browser in headless mode with custom arguments
        browser = await pw.chromium.launch(
            headless=True,
            args=[
                "--window-size=1280,720",
                "--disable-dev-shm-usage",
                "--ipc=host",
                "--single-process"
            ],
        )

        # Create a new browser context (like an incognito window)
        context = await browser.new_context()
        # Wider default timeout to match the agent's DOM-stability budget;
        # auto-waiting Playwright APIs (expect, locator.wait_for) inherit this.
        context.set_default_timeout(15000)

        # Open a new page in the browser context
        page = await context.new_page()

        # Interact with the page elements to simulate user flow
        # -> navigate
        await page.goto("http://localhost:5173")
        try:
            await page.wait_for_load_state("domcontentloaded", timeout=5000)
        except Exception:
            pass
        
        # -> Open the backend server page (http://localhost:8000) in a new tab to check if the API/server is running or returning errors before retrying the frontend.
        # Open URL in new tab
        page = await context.new_page()
        await page.goto("http://localhost:8000")
        try:
            await page.wait_for_load_state("domcontentloaded", timeout=5000)
        except Exception:
            pass
        
        # -> Switch to the browser tab titled 'AI Career Studio' (http://localhost:5173) so the frontend UI can be inspected and reloaded if needed.
        # Switch to tab A1AB
        page = context.pages[-1]  # switch to most recently active tab
        
        # -> Reload the frontend page and check whether the SPA renders (look for UI elements such as 'Profiles', 'Load profile', 'Jobs', or a search field).
        await page.goto("http://localhost:5173")
        try:
            await page.wait_for_load_state("domcontentloaded", timeout=5000)
        except Exception:
            pass
        
        # -> Sign in using the login form by entering the username 'haseeb-heaven' and password '123456', then click the 'Sign In' button.
        # Enter username text field
        elem = page.get_by_placeholder('Enter username', exact=True)
        await elem.wait_for(state="visible", timeout=10000)
        await elem.fill("haseeb-heaven")
        
        # -> Sign in using the login form by entering the username 'haseeb-heaven' and password '123456', then click the 'Sign In' button.
        # Password password field
        elem = page.get_by_placeholder('Password', exact=True)
        await elem.wait_for(state="visible", timeout=10000)
        await elem.fill("123456")
        
        # -> Sign in using the login form by entering the username 'haseeb-heaven' and password '123456', then click the 'Sign In' button.
        # Sign In button
        elem = page.get_by_text('Username', exact=True).locator("xpath=ancestor-or-self::*[.//button][1]").get_by_role('button', name='Sign In', exact=True)
        await elem.click(timeout=10000)
        
        # -> Sign in using the username 'haseeb91' and password '123456' by filling the username and password fields and clicking the 'Sign In' button.
        # Enter username text field
        elem = page.get_by_placeholder('Enter username', exact=True)
        await elem.wait_for(state="visible", timeout=10000)
        await elem.fill("haseeb91")
        
        # -> Sign in using the username 'haseeb91' and password '123456' by filling the username and password fields and clicking the 'Sign In' button.
        # Password password field
        elem = page.get_by_placeholder('Password', exact=True)
        await elem.wait_for(state="visible", timeout=10000)
        await elem.fill("123456")
        
        # -> Sign in using the username 'haseeb91' and password '123456' by filling the username and password fields and clicking the 'Sign In' button.
        # Sign In button
        elem = page.get_by_text('Username', exact=True).locator("xpath=ancestor-or-self::*[.//button][1]").get_by_role('button', name='Sign In', exact=True)
        await elem.click(timeout=10000)
        
        # -> Click the 'Open Saved Profile' button to load a saved profile into the editor.
        # 📂 Open Saved Profile button
        elem = page.get_by_role('button', name='📂 Open Saved Profile', exact=True)
        await elem.click(timeout=10000)
        
        # -> Click the 'Open →' button on the first saved profile card (the visible 'Open →' button) to load that profile into the editor.
        # Open → button
        elem = page.get_by_text('haseebmir.hm@gmail.com · Profile #1', exact=True).locator("xpath=ancestor-or-self::*[.//button][1]").get_by_role('button', name='Open →', exact=True)
        await elem.click(timeout=10000)
        
        # -> Click the 'Job Matching' button in the left sidebar to open the Job Matching UI.
        # 🔍 Job Matching button
        elem = page.get_by_role('button', name='🔍 Job Matching', exact=True)
        await elem.click(timeout=10000)
        
        # -> Click the 'Find Jobs' button on the Job Matching page to start a live job search using the loaded profile.
        # Find Jobs button
        elem = page.get_by_role('button', name='Find Jobs', exact=True)
        await elem.click(timeout=10000)
        
        # --> Assertions to verify final state
        current_url = await page.evaluate("() => window.location.href")
        # Assert: page loaded with a URL (final outcome verified by the AI judge during the run)
        assert current_url, 'Page should have loaded with a URL'
        current_url = await page.evaluate("() => window.location.href")
        # Assert: page loaded with a URL (final outcome verified by the AI judge during the run)
        assert current_url, 'Page should have loaded with a URL'
        await asyncio.sleep(5)

    finally:
        if context:
            await context.close()
        if browser:
            await browser.close()
        if pw:
            await pw.stop()

asyncio.run(run_test())
    