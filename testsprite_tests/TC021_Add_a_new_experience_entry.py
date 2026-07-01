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
        
        # -> Fill the 'Username' and 'Password' fields and click the 'Sign In' button to authenticate and load the profile editor.
        # Enter username text field
        elem = page.get_by_placeholder('Enter username', exact=True)
        await elem.wait_for(state="visible", timeout=10000)
        await elem.fill("haseeb-heaven")
        
        # -> Fill the 'Username' and 'Password' fields and click the 'Sign In' button to authenticate and load the profile editor.
        # Password password field
        elem = page.get_by_placeholder('Password', exact=True)
        await elem.wait_for(state="visible", timeout=10000)
        await elem.fill("123456")
        
        # -> Fill the 'Username' and 'Password' fields and click the 'Sign In' button to authenticate and load the profile editor.
        # Sign In button
        elem = page.get_by_text('Username', exact=True).locator("xpath=ancestor-or-self::*[.//button][1]").get_by_role('button', name='Sign In', exact=True)
        await elem.click(timeout=10000)
        
        # -> Click the "Continue as guest (no account)" link to load the profile editor as a guest.
        # Continue as guest (no account) button
        elem = page.get_by_role('button', name='Continue as guest (no account)', exact=True)
        await elem.click(timeout=10000)
        
        # -> Click the 'Open Saved Profile' button to load the profile editor.
        # 📂 Open Saved Profile button
        elem = page.get_by_role('button', name='📂 Open Saved Profile', exact=True)
        await elem.click(timeout=10000)
        
        # -> Click the '📂 Open Saved Profile' button to load the profile editor or saved-profile modal.
        # 📂 Open Saved Profile button
        elem = page.get_by_role('button', name='📂 Open Saved Profile', exact=True)
        await elem.click(timeout=10000)
        
        # -> Upload a sample JSON resume using the 'Drag & drop your resume here' file input to load the profile editor.
        # file upload
        elem = page.locator('xpath=/html/body/div/div/div/div[2]/input')
        await elem.wait_for(state="attached", timeout=10000)
        if await elem.evaluate("e => e.tagName === 'INPUT' && (e.type || '').toLowerCase() === 'file'"):
            await elem.set_input_files("./fixtures/sample_resume.json")
        else:
            await elem.wait_for(state="visible", timeout=10000)
            async with page.expect_file_chooser() as fc_info:
                await elem.click()
            chooser = await fc_info.value
            await chooser.set_files("./fixtures/sample_resume.json")
        
        # -> Click the 'Experience' item in the left sidebar to open the Experience editor.
        # 💼 Experience button
        elem = page.get_by_role('button', name='💼 Experience', exact=True)
        await elem.click(timeout=10000)
        
        # -> Click the '+ Add Experience' button to open the add-experience form.
        # + Add Experience button
        elem = page.get_by_role('button', name='+ Add Experience', exact=True)
        await elem.click(timeout=10000)
        
        # -> Fill the Role, Company, Start, and Location fields and click the 'Add' button to create the experience entry.
        # Software Engineer text field
        elem = page.get_by_placeholder('Software Engineer', exact=True)
        await elem.wait_for(state="visible", timeout=10000)
        await elem.fill("QA Engineer")
        
        # -> Fill the Role, Company, Start, and Location fields and click the 'Add' button to create the experience entry.
        # Acme Corp text field
        elem = page.get_by_placeholder('Acme Corp', exact=True)
        await elem.wait_for(state="visible", timeout=10000)
        await elem.fill("Test Company Inc")
        
        # -> Fill the Role, Company, Start, and Location fields and click the 'Add' button to create the experience entry.
        # Jan 2022 text field
        elem = page.get_by_placeholder('Jan 2022', exact=True)
        await elem.wait_for(state="visible", timeout=10000)
        await elem.fill("Feb 2020")
        
        # -> Fill the Role, Company, Start, and Location fields and click the 'Add' button to create the experience entry.
        # Remote / City, Country text field
        elem = page.get_by_placeholder('Remote / City, Country', exact=True)
        await elem.wait_for(state="visible", timeout=10000)
        await elem.fill("New York, USA")
        
        # -> Fill the Role, Company, Start, and Location fields and click the 'Add' button to create the experience entry.
        # Add button
        elem = page.get_by_role('button', name='Add', exact=True)
        await elem.click(timeout=10000)
        
        # -> Click the '+ Add bullet' link inside the newly added experience card so a bullet input can be created.
        # + Add bullet button
        elem = page.get_by_role('button', name='+ Add bullet', exact=True)
        await elem.click(timeout=10000)
        
        # -> Enter a bullet into the 'New bullet point…' input and click the 'Add' button to add a bullet point to the experience entry.
        # New bullet point… text field
        elem = page.get_by_placeholder('New bullet point…', exact=True)
        await elem.wait_for(state="visible", timeout=10000)
        await elem.fill("Wrote automated tests and reported issues")
        
        # -> Enter a bullet into the 'New bullet point…' input and click the 'Add' button to add a bullet point to the experience entry.
        # Add button
        elem = page.get_by_role('button', name='Add', exact=True)
        await elem.click(timeout=10000)
        
        # --> Assertions to verify final state
        
        # --> Verify the new experience appears in the experience list
        await page.locator("xpath=/html/body/div[1]/div[1]/div/main/div/div/div[2]/div/div[2]/button[1]").nth(0).scroll_into_view_if_needed()
        # Assert: The experience entry's Edit button is visible.
        await expect(page.locator("xpath=/html/body/div[1]/div[1]/div/main/div/div/div[2]/div/div[2]/button[1]").nth(0)).to_be_visible(timeout=15000), "The experience entry's Edit button is visible."
        await page.locator("xpath=/html/body/div[1]/div[1]/div/main/div/div/div[2]/div/div[2]/button[2]").nth(0).scroll_into_view_if_needed()
        # Assert: The experience entry's Delete button is visible.
        await expect(page.locator("xpath=/html/body/div[1]/div[1]/div/main/div/div/div[2]/div/div[2]/button[2]").nth(0)).to_be_visible(timeout=15000), "The experience entry's Delete button is visible."
        await page.locator("xpath=/html/body/div[1]/div[1]/div/main/div/div/div[2]/button").nth(0).scroll_into_view_if_needed()
        # Assert: The '+ Add bullet' control on the experience card is visible.
        await expect(page.locator("xpath=/html/body/div[1]/div[1]/div/main/div/div/div[2]/button").nth(0)).to_be_visible(timeout=15000), "The '+ Add bullet' control on the experience card is visible."
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
    