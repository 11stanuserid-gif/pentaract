#!/usr/bin/env python3
"""Complete genspark signup flow via Azure AD B2C"""
import asyncio
from playwright.async_api import async_playwright

async def signup():
    pw = await async_playwright().start()
    browser = await pw.chromium.launch(headless=True, args=['--no-sandbox', '--disable-blink-features=AutomationControlled'])
    context = await browser.new_context(
        viewport={'width': 1920, 'height': 1080},
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36'
    )
    await context.add_init_script("Object.defineProperty(navigator, 'webdriver', { get: () => undefined });")
    
    page = await context.new_page()
    
    # Go to genspark login page
    await page.goto('https://www.genspark.ai/login', wait_until='networkidle', timeout=60000)
    await asyncio.sleep(3)
    
    print(f"Current URL: {page.url}")
    
    # Check what's visible
    await page.screenshot(path='/opt/render/reports/signup_step1.png', full_page=True)
    
    # Look for the "Login with email" button and click it
    email_login_btn = page.locator('text=Login with email')
    if await email_login_btn.is_visible():
        await email_login_btn.click()
        await asyncio.sleep(3)
        print(f"After clicking 'Login with email': {page.url}")
        
        await page.screenshot(path='/opt/render/reports/signup_step2_email.png', full_page=True)
        
        # Look for email input
        email_input = await page.query_selector('input[type="email"]')
        if email_input:
            print("Found email input!")
            await email_input.fill('testuser@example.com')
        else:
            # Check all inputs
            inputs = await page.evaluate('''() => {
                return Array.from(document.querySelectorAll('input')).map(el => ({
                    tag: el.tagName,
                    type: el.type,
                    id: el.id,
                    name: el.name,
                    placeholder: el.placeholder,
                    autocomplete: el.autocomplete,
                    visible: el.offsetParent !== null,
                    rect: el.getBoundingClientRect()
                }));
            }''')
            for inp in inputs:
                print(f"  Input: type={inp['type']} id={inp['id']} name={inp['name']} placeholder={inp['placeholder']} visible={inp['visible']} rect=({inp['rect']['x']:.0f},{inp['rect']['y']:.0f})")
    
    # Also dump all interactive elements
    els = await page.evaluate('''() => {
        const all = document.querySelectorAll('form, input, button, a, select, div[role="button"]');
        return Array.from(all).map(el => ({
            tag: el.tagName,
            type: el.type || '',
            id: el.id || '',
            text: (el.textContent || '').trim().slice(0, 80),
            visible: el.offsetParent !== null,
            w: el.getBoundingClientRect().width,
            h: el.getBoundingClientRect().height,
            y: el.getBoundingClientRect().y
        })).filter(e => e.visible && e.w > 0 && e.h > 0 && (e.text || e.id || e.type))
            .sort((a, b) => a.y - b.y);
    }''')
    
    print(f"\nAll interactive elements ({len(els)}):")
    for e in els:
        if e['text'] or e['id']:
            print(f"  y={e['y']:.0f} {e['tag']:6s} type={e['type']:12s} id={e['id']:30s} text=\"{e['text'][:50]}\"")
    
    await page.screenshot(path='/opt/render/reports/signup_step_final.png', full_page=True)
    await browser.close()
    await pw.stop()

asyncio.run(signup())
