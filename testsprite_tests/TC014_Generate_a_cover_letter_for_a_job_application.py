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
        
        # -> Wait 5 seconds for the frontend app to finish loading, then reload the homepage (click refresh) to attempt to load the SPA and reveal interactive elements such as the profile editor or 'Cover Letter' controls.
        await page.goto("http://localhost:5173/")
        try:
            await page.wait_for_load_state("domcontentloaded", timeout=5000)
        except Exception:
            pass
        
        # -> Fill the Username field with 'haseeb-heaven', fill the Password field with '123456', then click the 'Sign In' button to authenticate and reach the app's main UI.
        # Enter username text field
        elem = page.get_by_placeholder('Enter username', exact=True)
        await elem.wait_for(state="visible", timeout=10000)
        await elem.fill("haseeb-heaven")
        
        # -> Fill the Username field with 'haseeb-heaven', fill the Password field with '123456', then click the 'Sign In' button to authenticate and reach the app's main UI.
        # Password password field
        elem = page.get_by_placeholder('Password', exact=True)
        await elem.wait_for(state="visible", timeout=10000)
        await elem.fill("123456")
        
        # -> Fill the Username field with 'haseeb-heaven', fill the Password field with '123456', then click the 'Sign In' button to authenticate and reach the app's main UI.
        # Sign In button
        elem = page.get_by_text('Username', exact=True).locator("xpath=ancestor-or-self::*[.//button][1]").get_by_role('button', name='Sign In', exact=True)
        await elem.click(timeout=10000)
        
        # -> Retry signing in by replacing the Username with 'haseeb91', entering Password '123456', and clicking the 'Sign In' button.
        # Enter username text field
        elem = page.get_by_placeholder('Enter username', exact=True)
        await elem.wait_for(state="visible", timeout=10000)
        await elem.fill("haseeb91")
        
        # -> Retry signing in by replacing the Username with 'haseeb91', entering Password '123456', and clicking the 'Sign In' button.
        # Password password field
        elem = page.get_by_placeholder('Password', exact=True)
        await elem.wait_for(state="visible", timeout=10000)
        await elem.fill("123456")
        
        # -> Retry signing in by replacing the Username with 'haseeb91', entering Password '123456', and clicking the 'Sign In' button.
        # Sign In button
        elem = page.get_by_text('Username', exact=True).locator("xpath=ancestor-or-self::*[.//button][1]").get_by_role('button', name='Sign In', exact=True)
        await elem.click(timeout=10000)
        
        # -> Click the 'Open Saved Profile' button to load a saved profile into the editor so the Cover Letters section can be used.
        # 📂 Open Saved Profile button
        elem = page.get_by_role('button', name='📂 Open Saved Profile', exact=True)
        await elem.click(timeout=10000)
        
        # -> Open the first saved profile by clicking the 'Open →' button on the top (first) saved profile card so the profile editor loads.
        # Open → button
        elem = page.get_by_text('haseebmir.hm@gmail.com · Profile #1', exact=True).locator("xpath=ancestor-or-self::*[.//button][1]").get_by_role('button', name='Open →', exact=True)
        await elem.click(timeout=10000)
        
        # -> Click the 'Cover Letter' button in the left sidebar to open the Cover Letter panel so job title and company input fields and the Generate control become visible.
        # ✍️ Cover Letter button
        elem = page.get_by_role('button', name='✍️ Cover Letter', exact=True)
        await elem.click(timeout=10000)
        
        # -> Fill the 'Job Title' field with 'Senior Software Engineer', fill the 'Company' field with 'Acme Corp', then click the 'Generate Cover Letter' button to create the cover letter.
        # e.g. Senior Software Engineer text field
        elem = page.get_by_placeholder('e.g. Senior Software Engineer', exact=True)
        await elem.wait_for(state="visible", timeout=10000)
        await elem.fill("Senior Software Engineer")
        
        # -> Fill the 'Job Title' field with 'Senior Software Engineer', fill the 'Company' field with 'Acme Corp', then click the 'Generate Cover Letter' button to create the cover letter.
        # e.g. Acme Corp text field
        elem = page.get_by_placeholder('e.g. Acme Corp', exact=True)
        await elem.wait_for(state="visible", timeout=10000)
        await elem.fill("Acme Corp")
        
        # -> Fill the 'Job Title' field with 'Senior Software Engineer', fill the 'Company' field with 'Acme Corp', then click the 'Generate Cover Letter' button to create the cover letter.
        # Generate Cover Letter button
        elem = page.get_by_role('button', name='Generate Cover Letter', exact=True)
        await elem.click(timeout=10000)
        
        # --> Assertions to verify final state
        
        # --> Verify the generated cover letter is displayed
        # Assert: The Job Title field contains 'Senior Software Engineer'.
        await expect(page.locator("xpath=/html/body/div/div[1]/div/main/div/div/div[1]/div[1]/input").nth(0)).to_have_value("Senior Software Engineer", timeout=15000), "The Job Title field contains 'Senior Software Engineer'."
        # Assert: The Company field contains 'Acme Corp'.
        await expect(page.locator("xpath=/html/body/div/div[1]/div/main/div/div/div[1]/div[2]/input").nth(0)).to_have_value("Acme Corp", timeout=15000), "The Company field contains 'Acme Corp'."
        await page.locator("xpath=/html/body/div/div[1]/div/main/div/div/div[3]/div/div/div/button[1]").nth(0).scroll_into_view_if_needed()
        # Assert: A generated cover letter entry is visible (the 'View' button is present).
        await expect(page.locator("xpath=/html/body/div/div[1]/div/main/div/div/div[3]/div/div/div/button[1]").nth(0)).to_be_visible(timeout=15000), "A generated cover letter entry is visible (the 'View' button is present)."
        await asyncio.sleep(5)

    finally:
        if context:
            await context.close()
        if browser:
            await browser.close()
        if pw:
            await pw.stop()

asyncio.run(run_test())
    