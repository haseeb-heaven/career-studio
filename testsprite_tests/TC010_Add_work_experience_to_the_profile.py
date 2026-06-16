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
        
        # -> Click the "Continue as guest (no account)" link on the sign-in card to enter the app without logging in.
        # Continue as guest (no account) button
        elem = page.get_by_role('button', name='Continue as guest (no account)', exact=True)
        await elem.click(timeout=10000)
        
        # -> Scroll down one full page to reveal additional navigation links and the Profile Editor or Experience section so the profile editor can be opened.
        await page.mouse.wheel(0, 300)
        
        # -> Click the '📂 Open Saved Profile' button to open the saved profiles dialog or navigate to the profile editor.
        # 📂 Open Saved Profile button
        elem = page.get_by_role('button', name='📂 Open Saved Profile', exact=True)
        await elem.click(timeout=10000)
        
        # -> Click the '📂 Open Saved Profile' button to open the saved profiles dialog or profile editor so a profile can be loaded.
        # 📂 Open Saved Profile button
        elem = page.get_by_role('button', name='📂 Open Saved Profile', exact=True)
        await elem.click(timeout=10000)
        
        # -> Click the 'Open Saved Profile' button to open the saved profiles dialog so a profile can be loaded.
        # 📂 Open Saved Profile button
        elem = page.get_by_role('button', name='📂 Open Saved Profile', exact=True)
        await elem.click(timeout=10000)
        
        # -> Click the '📂 Open Saved Profile' button to open the saved profiles dialog or profile editor and verify the dialog appears.
        # 📂 Open Saved Profile button
        elem = page.get_by_role('button', name='📂 Open Saved Profile', exact=True)
        await elem.click(timeout=10000)
        
        # -> Click the '📂 Open Saved Profile' button in the header to open the saved profiles dialog or profile editor.
        # 📂 Open Saved Profile button
        elem = page.get_by_role('button', name='📂 Open Saved Profile', exact=True)
        await elem.click(timeout=10000)
        
        # -> Upload a minimal resume JSON using the page's 'Browse Files' / file input control to load a profile into the editor and trigger the profile editor to appear.
        # file upload
        elem = page.locator('xpath=/html/body/div/div/div/div[2]/input')
        await elem.wait_for(state="attached", timeout=10000)
        if await elem.evaluate("e => e.tagName === 'INPUT' && (e.type || '').toLowerCase() === 'file'"):
            await elem.set_input_files("./fixtures/resume.json")
        else:
            await elem.wait_for(state="visible", timeout=10000)
            async with page.expect_file_chooser() as fc_info:
                await elem.click()
            chooser = await fc_info.value
            await chooser.set_files("./fixtures/resume.json")
        
        # -> Open the 'Experience' section by clicking the 'Experience' tab in the left sidebar to reveal the experience editor and controls.
        # 💼 Experience button
        elem = page.get_by_role('button', name='💼 Experience', exact=True)
        await elem.click(timeout=10000)
        
        # -> Click the '+ Add Experience' button to open the Add Experience form so job details can be entered.
        # + Add Experience button
        elem = page.get_by_role('button', name='+ Add Experience', exact=True)
        await elem.click(timeout=10000)
        
        # -> Fill the 'Role', 'Company', 'Start', and 'End' fields in the 'New Experience' form and click the 'Add' button to create the experience entry.
        # Software Engineer text field
        elem = page.get_by_placeholder('Software Engineer', exact=True)
        await elem.wait_for(state="visible", timeout=10000)
        await elem.fill("QA Engineer")
        
        # -> Fill the 'Role', 'Company', 'Start', and 'End' fields in the 'New Experience' form and click the 'Add' button to create the experience entry.
        # Acme Corp text field
        elem = page.get_by_placeholder('Acme Corp', exact=True)
        await elem.wait_for(state="visible", timeout=10000)
        await elem.fill("Acme Corp")
        
        # -> Fill the 'Role', 'Company', 'Start', and 'End' fields in the 'New Experience' form and click the 'Add' button to create the experience entry.
        # Jan 2022 text field
        elem = page.get_by_placeholder('Jan 2022', exact=True)
        await elem.wait_for(state="visible", timeout=10000)
        await elem.fill("Jan 2020")
        
        # -> Fill the 'Role', 'Company', 'Start', and 'End' fields in the 'New Experience' form and click the 'Add' button to create the experience entry.
        # Present text field
        elem = page.get_by_placeholder('Present', exact=True)
        await elem.wait_for(state="visible", timeout=10000)
        await elem.fill("Dec 2022")
        
        # -> Fill the 'Role', 'Company', 'Start', and 'End' fields in the 'New Experience' form and click the 'Add' button to create the experience entry.
        # Add button
        elem = page.get_by_role('button', name='Add', exact=True)
        await elem.click(timeout=10000)
        
        # -> Click the 'Edit' button on the newly created experience card to open the edit form and check for a Location field (then add location if present).
        # Edit button
        elem = page.get_by_role('button', name='Edit', exact=True)
        await elem.click(timeout=10000)
        
        # -> Fill the 'Location' field with 'San Francisco, CA' and click the 'Save' button to save the experience entry.
        # text field
        elem = page.locator('xpath=/html/body/div/div/div/main/div/div/div[2]/div/div/div[5]/input')
        await elem.wait_for(state="visible", timeout=10000)
        await elem.fill("San Francisco, CA")
        
        # -> Fill the 'Location' field with 'San Francisco, CA' and click the 'Save' button to save the experience entry.
        # Save button
        elem = page.get_by_role('button', name='Save', exact=True)
        await elem.click(timeout=10000)
        
        # --> Assertions to verify final state
        
        # --> Verify the new experience entry appears in the experience list
        await page.locator("xpath=/html/body/div[1]/div[1]/div/main/div/div/div[2]/div/div[2]/button[1]").nth(0).scroll_into_view_if_needed()
        # Assert: The newly added experience entry appears in the list (Edit button is visible).
        await expect(page.locator("xpath=/html/body/div[1]/div[1]/div/main/div/div/div[2]/div/div[2]/button[1]").nth(0)).to_be_visible(timeout=15000), "The newly added experience entry appears in the list (Edit button is visible)."
        await asyncio.sleep(5)

    finally:
        if context:
            await context.close()
        if browser:
            await browser.close()
        if pw:
            await pw.stop()

asyncio.run(run_test())
    