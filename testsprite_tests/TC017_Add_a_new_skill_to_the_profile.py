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
        
        # -> Click the 'Continue as guest (no account)' link to enter the app without signing in.
        # Continue as guest (no account) button
        elem = page.get_by_role('button', name='Continue as guest (no account)', exact=True)
        await elem.click(timeout=10000)
        
        # -> Click the 'Open Saved Profile' button to load a profile in the editor.
        # 📂 Open Saved Profile button
        elem = page.get_by_role('button', name='📂 Open Saved Profile', exact=True)
        await elem.click(timeout=10000)
        
        # -> Upload the saved profile JSON using the file picker opened by 'Open Saved Profile' (select the sample_profile.json file).
        # file upload
        elem = page.locator('xpath=/html/body/div/div/div/div[2]/input')
        await elem.wait_for(state="attached", timeout=10000)
        if await elem.evaluate("e => e.tagName === 'INPUT' && (e.type || '').toLowerCase() === 'file'"):
            await elem.set_input_files("./fixtures/sample_profile.json")
        else:
            await elem.wait_for(state="visible", timeout=10000)
            async with page.expect_file_chooser() as fc_info:
                await elem.click()
            chooser = await fc_info.value
            await chooser.set_files("./fixtures/sample_profile.json")
        
        # -> Click the 'Skills' button in the left sidebar to open the Skills section.
        # ⚡ Skills button
        elem = page.get_by_role('button', name='⚡ Skills', exact=True)
        await elem.click(timeout=10000)
        
        # -> Click the '+ Add Skill' button to open the Add Skill form.
        # + Add Skill button
        elem = page.get_by_role('button', name='+ Add Skill', exact=True)
        await elem.click(timeout=10000)
        
        # -> Fill 'JavaScript' into the Skill name field, 'Programming' into the Category field, set Years to '3', then click the 'Add' button.
        # Skill name text field
        elem = page.get_by_placeholder('Skill name', exact=True)
        await elem.wait_for(state="visible", timeout=10000)
        await elem.fill("JavaScript")
        
        # -> Fill 'JavaScript' into the Skill name field, 'Programming' into the Category field, set Years to '3', then click the 'Add' button.
        # Category text field
        elem = page.get_by_placeholder('Category', exact=True)
        await elem.wait_for(state="visible", timeout=10000)
        await elem.fill("Programming")
        
        # -> Fill 'JavaScript' into the Skill name field, 'Programming' into the Category field, set Years to '3', then click the 'Add' button.
        # 0 number field
        elem = page.get_by_placeholder('0', exact=True)
        await elem.wait_for(state="visible", timeout=10000)
        await elem.fill("3")
        
        # -> Fill 'JavaScript' into the Skill name field, 'Programming' into the Category field, set Years to '3', then click the 'Add' button.
        # Add button
        elem = page.get_by_role('button', name='Add', exact=True)
        await elem.click(timeout=10000)
        
        # --> Assertions to verify final state
        
        # --> Verify the new skill appears in the skills list
        # Assert: The skills list shows the new skill name 'JavaScript'.
        await expect(page.locator("xpath=/html/body/div[1]/div[1]/div/main/div/div/table/tbody/tr/td[1]").nth(0)).to_have_text("JavaScript", timeout=15000), "The skills list shows the new skill name 'JavaScript'."
        # Assert: The skills list shows the new skill category 'Programming'.
        await expect(page.locator("xpath=/html/body/div[1]/div[1]/div/main/div/div/table/tbody/tr/td[2]").nth(0)).to_have_text("Programming", timeout=15000), "The skills list shows the new skill category 'Programming'."
        # Assert: The skills list shows the new skill years of experience '3'.
        await expect(page.locator("xpath=/html/body/div[1]/div[1]/div/main/div/div/table/tbody/tr/td[3]").nth(0)).to_have_text("3", timeout=15000), "The skills list shows the new skill years of experience '3'."
        await asyncio.sleep(5)

    finally:
        if context:
            await context.close()
        if browser:
            await browser.close()
        if pw:
            await pw.stop()

asyncio.run(run_test())
    