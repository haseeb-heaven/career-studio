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
        
        # -> Reload the application root page to allow the SPA to finish loading (refresh the page at http://localhost:5173).
        await page.goto("http://localhost:5173/")
        try:
            await page.wait_for_load_state("domcontentloaded", timeout=5000)
        except Exception:
            pass
        
        # -> Enter username 'haseeb-heaven' into the Username field, enter password '123456' into the Password field, then click the 'Sign In' button to log in and load the profile editor.
        # Enter username text field
        elem = page.get_by_placeholder('Enter username', exact=True)
        await elem.wait_for(state="visible", timeout=10000)
        await elem.fill("haseeb-heaven")
        
        # -> Enter username 'haseeb-heaven' into the Username field, enter password '123456' into the Password field, then click the 'Sign In' button to log in and load the profile editor.
        # Password password field
        elem = page.get_by_placeholder('Password', exact=True)
        await elem.wait_for(state="visible", timeout=10000)
        await elem.fill("123456")
        
        # -> Enter username 'haseeb-heaven' into the Username field, enter password '123456' into the Password field, then click the 'Sign In' button to log in and load the profile editor.
        # Sign In button
        elem = page.get_by_text('Username', exact=True).locator("xpath=ancestor-or-self::*[.//button][1]").get_by_role('button', name='Sign In', exact=True)
        await elem.click(timeout=10000)
        
        # -> Fill the Username field with 'haseeb91', fill the Password field with '123456', and click the 'Sign In' button to log in and load the profile editor.
        # Enter username text field
        elem = page.get_by_placeholder('Enter username', exact=True)
        await elem.wait_for(state="visible", timeout=10000)
        await elem.fill("haseeb91")
        
        # -> Fill the Username field with 'haseeb91', fill the Password field with '123456', and click the 'Sign In' button to log in and load the profile editor.
        # Password password field
        elem = page.get_by_placeholder('Password', exact=True)
        await elem.wait_for(state="visible", timeout=10000)
        await elem.fill("123456")
        
        # -> Fill the Username field with 'haseeb91', fill the Password field with '123456', and click the 'Sign In' button to log in and load the profile editor.
        # Sign In button
        elem = page.get_by_text('Username', exact=True).locator("xpath=ancestor-or-self::*[.//button][1]").get_by_role('button', name='Sign In', exact=True)
        await elem.click(timeout=10000)
        
        # -> Click the 'Open Saved Profile' button to load a saved profile into the profile editor so the Skills section can be opened.
        # 📂 Open Saved Profile button
        elem = page.get_by_role('button', name='📂 Open Saved Profile', exact=True)
        await elem.click(timeout=10000)
        
        # -> Click the 'Open →' button on the first saved profile card to load that profile into the profile editor.
        # Open → button
        elem = page.get_by_text('haseebmir.hm@gmail.com · Profile #1', exact=True).locator("xpath=ancestor-or-self::*[.//button][1]").get_by_role('button', name='Open →', exact=True)
        await elem.click(timeout=10000)
        
        # -> Click the 'Skills' button in the left sidebar to open the Skills section of the profile editor.
        # ⚡ Skills button
        elem = page.get_by_role('button', name='⚡ Skills', exact=True)
        await elem.click(timeout=10000)
        
        # -> Open the 'Add Skill' dialog by clicking the '+ Add Skill' button on the Skills page so the fields for Name, Category, and Years can be filled.
        # + Add Skill button
        elem = page.get_by_role('button', name='+ Add Skill', exact=True)
        await elem.click(timeout=10000)
        
        # -> Fill the Skill name field with 'JavaScript', fill the Category field with 'Programming', set Years to '3', then click the 'Add' button to add the skill.
        # Skill name text field
        elem = page.get_by_placeholder('Skill name', exact=True)
        await elem.wait_for(state="visible", timeout=10000)
        await elem.fill("JavaScript")
        
        # -> Fill the Skill name field with 'JavaScript', fill the Category field with 'Programming', set Years to '3', then click the 'Add' button to add the skill.
        # Category text field
        elem = page.get_by_placeholder('Category', exact=True)
        await elem.wait_for(state="visible", timeout=10000)
        await elem.fill("Programming")
        
        # -> Fill the Skill name field with 'JavaScript', fill the Category field with 'Programming', set Years to '3', then click the 'Add' button to add the skill.
        # 0 number field
        elem = page.get_by_placeholder('0', exact=True)
        await elem.wait_for(state="visible", timeout=10000)
        await elem.fill("3")
        
        # -> Fill the Skill name field with 'JavaScript', fill the Category field with 'Programming', set Years to '3', then click the 'Add' button to add the skill.
        # Add button
        elem = page.get_by_role('button', name='Add', exact=True)
        await elem.click(timeout=10000)
        
        # --> Assertions to verify final state
        
        # --> Verify the new skill appears in the skills list
        # Assert: The skills list shows the new skill name 'JavaScript'.
        await expect(page.locator("xpath=/html/body/div[1]/div[1]/div/main/div/div/table/tbody/tr/td[1]").nth(0)).to_have_text("JavaScript", timeout=15000), "The skills list shows the new skill name 'JavaScript'."
        # Assert: The skills list shows the category 'Programming' for the new skill.
        await expect(page.locator("xpath=/html/body/div[1]/div[1]/div/main/div/div/table/tbody/tr/td[2]").nth(0)).to_have_text("Programming", timeout=15000), "The skills list shows the category 'Programming' for the new skill."
        # Assert: The skills list shows '3' years of experience for the new skill.
        await expect(page.locator("xpath=/html/body/div[1]/div[1]/div/main/div/div/table/tbody/tr/td[3]").nth(0)).to_have_text("3", timeout=15000), "The skills list shows '3' years of experience for the new skill."
        await asyncio.sleep(5)

    finally:
        if context:
            await context.close()
        if browser:
            await browser.close()
        if pw:
            await pw.stop()

asyncio.run(run_test())
    