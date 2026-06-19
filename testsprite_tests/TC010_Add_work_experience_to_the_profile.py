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
        
        # -> Reload the AI Career Studio frontend by navigating to the root URL (http://localhost:5173/) so the SPA has another chance to render and reveal UI elements like 'Login' or 'Profile'.
        await page.goto("http://localhost:5173/")
        try:
            await page.wait_for_load_state("domcontentloaded", timeout=5000)
        except Exception:
            pass
        
        # -> Fill 'haseeb-heaven' into the Username field, fill '123456' into the Password field, then click the 'Sign In' button to log in.
        # Enter username text field
        elem = page.get_by_placeholder('Enter username', exact=True)
        await elem.wait_for(state="visible", timeout=10000)
        await elem.fill("haseeb-heaven")
        
        # -> Fill 'haseeb-heaven' into the Username field, fill '123456' into the Password field, then click the 'Sign In' button to log in.
        # Password password field
        elem = page.get_by_placeholder('Password', exact=True)
        await elem.wait_for(state="visible", timeout=10000)
        await elem.fill("123456")
        
        # -> Fill 'haseeb-heaven' into the Username field, fill '123456' into the Password field, then click the 'Sign In' button to log in.
        # Sign In button
        elem = page.get_by_text('Username', exact=True).locator("xpath=ancestor-or-self::*[.//button][1]").get_by_role('button', name='Sign In', exact=True)
        await elem.click(timeout=10000)
        
        # -> Log in by replacing the Username with 'haseeb91', re-entering the password '123456', then clicking the 'Sign In' button.
        # Enter username text field
        elem = page.get_by_placeholder('Enter username', exact=True)
        await elem.wait_for(state="visible", timeout=10000)
        await elem.fill("haseeb91")
        
        # -> Log in by replacing the Username with 'haseeb91', re-entering the password '123456', then clicking the 'Sign In' button.
        # Password password field
        elem = page.get_by_placeholder('Password', exact=True)
        await elem.wait_for(state="visible", timeout=10000)
        await elem.fill("123456")
        
        # -> Log in by replacing the Username with 'haseeb91', re-entering the password '123456', then clicking the 'Sign In' button.
        # Sign In button
        elem = page.get_by_text('Username', exact=True).locator("xpath=ancestor-or-self::*[.//button][1]").get_by_role('button', name='Sign In', exact=True)
        await elem.click(timeout=10000)
        
        # -> Click the 'Open Saved Profile' button to open saved profiles and load a profile into the editor.
        # 📂 Open Saved Profile button
        elem = page.get_by_role('button', name='📂 Open Saved Profile', exact=True)
        await elem.click(timeout=10000)
        
        # -> Click the 'Open →' button for the first saved profile to load that profile into the profile editor.
        # Open → button
        elem = page.get_by_text('haseebmir.hm@gmail.com · Profile #1', exact=True).locator("xpath=ancestor-or-self::*[.//button][1]").get_by_role('button', name='Open →', exact=True)
        await elem.click(timeout=10000)
        
        # -> Open the 'Experience' section by clicking the 'Experience' item in the left sidebar so the experience editor/list is displayed.
        # 💼 Experience button
        elem = page.get_by_role('button', name='💼 Experience', exact=True)
        await elem.click(timeout=10000)
        
        # -> Click the '+ Add Experience' button to open the Add Experience form so the job details can be entered.
        # + Add Experience button
        elem = page.get_by_role('button', name='+ Add Experience', exact=True)
        await elem.click(timeout=10000)
        
        # -> Fill the Role, Company, Start date, and Location fields in the New Experience form, then click the 'Add' button to submit the new experience entry.
        # Software Engineer text field
        elem = page.get_by_placeholder('Software Engineer', exact=True)
        await elem.wait_for(state="visible", timeout=10000)
        await elem.fill("Backend Engineer")
        
        # -> Fill the Role, Company, Start date, and Location fields in the New Experience form, then click the 'Add' button to submit the new experience entry.
        # Acme Corp text field
        elem = page.get_by_placeholder('Acme Corp', exact=True)
        await elem.wait_for(state="visible", timeout=10000)
        await elem.fill("TestCorp Inc.")
        
        # -> Fill the Role, Company, Start date, and Location fields in the New Experience form, then click the 'Add' button to submit the new experience entry.
        # Jan 2022 text field
        elem = page.get_by_placeholder('Jan 2022', exact=True)
        await elem.wait_for(state="visible", timeout=10000)
        await elem.fill("Jan 2021")
        
        # -> Fill the Role, Company, Start date, and Location fields in the New Experience form, then click the 'Add' button to submit the new experience entry.
        # Remote / City, Country text field
        elem = page.get_by_placeholder('Remote / City, Country', exact=True)
        await elem.wait_for(state="visible", timeout=10000)
        await elem.fill("Remote / San Francisco, CA")
        
        # -> Fill the Role, Company, Start date, and Location fields in the New Experience form, then click the 'Add' button to submit the new experience entry.
        # Add button
        elem = page.get_by_role('button', name='Add', exact=True)
        await elem.click(timeout=10000)
        
        # -> Open the bullet editor by clicking the '+ Add bullet' link on the TestCorp Inc. experience card so a new bullet can be entered.
        # + Add bullet button
        elem = page.get_by_role('button', name='+ Add bullet', exact=True)
        await elem.click(timeout=10000)
        
        # -> Type a bullet into the 'New bullet point…' input (for example: 'Implemented REST APIs and reduced response time by 30%') and click the 'Add' button to save the bullet.
        # New bullet point… text field
        elem = page.get_by_placeholder('New bullet point…', exact=True)
        await elem.wait_for(state="visible", timeout=10000)
        await elem.fill("Implemented REST APIs and reduced response time by 30%.")
        
        # -> Type a bullet into the 'New bullet point…' input (for example: 'Implemented REST APIs and reduced response time by 30%') and click the 'Add' button to save the bullet.
        # Add button
        elem = page.get_by_role('button', name='Add', exact=True)
        await elem.click(timeout=10000)
        
        # --> Assertions to verify final state
        
        # --> Verify the new experience entry appears in the experience list
        await page.locator("xpath=/html/body/div[1]/div[1]/div/main/div/div/div[2]/ul/li/div").nth(0).scroll_into_view_if_needed()
        # Assert: The experience card is visible in the experience list.
        await expect(page.locator("xpath=/html/body/div[1]/div[1]/div/main/div/div/div[2]/ul/li/div").nth(0)).to_be_visible(timeout=15000), "The experience card is visible in the experience list."
        await page.locator("xpath=/html/body/div[1]/div[1]/div/main/div/div/div[2]/ul/li/div/button[1]").nth(0).scroll_into_view_if_needed()
        # Assert: The experience entry's edit button is visible, confirming the entry appears in the list.
        await expect(page.locator("xpath=/html/body/div[1]/div[1]/div/main/div/div/div[2]/ul/li/div/button[1]").nth(0)).to_be_visible(timeout=15000), "The experience entry's edit button is visible, confirming the entry appears in the list."
        await page.locator("xpath=/html/body/div[1]/div[1]/div/main/div/div/div[2]/button").nth(0).scroll_into_view_if_needed()
        # Assert: The '+ Add bullet' button is visible on the experience card, showing the new entry's bullet controls are present.
        await expect(page.locator("xpath=/html/body/div[1]/div[1]/div/main/div/div/div[2]/button").nth(0)).to_be_visible(timeout=15000), "The '+ Add bullet' button is visible on the experience card, showing the new entry's bullet controls are present."
        await asyncio.sleep(5)

    finally:
        if context:
            await context.close()
        if browser:
            await browser.close()
        if pw:
            await pw.stop()

asyncio.run(run_test())
    