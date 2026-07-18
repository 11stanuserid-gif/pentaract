#!/usr/bin/env python3
"""Probe the Azure B2C signup flow on genspark"""
import asyncio
from playwright.async_api import async_playwright

async def main():
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
    print(f"Initial URL: {page.url}")

    # Click "Sign up now" 
    signup_link = page.locator('#createAccount')
    if await signup_link.is_visible():
        print("Clicking 'Sign up now'...")
        await signup_link.click()
        await asyncio.sleep(5)
        print(f"After click URL: {page.url}")
        await page.screenshot(path='/opt/render/reports/signup_step1.png', full_page=True)
        
        # Check for signup form fields
        inputs = await page.evaluate('''() => {
            return Array.from(document.querySelectorAll('input, select, button')).map(el => ({
                tag: el.tagName,
                type: el.type || '',
                id: el.id || '',
                name: el.name || '',
                placeholder: el.placeholder || '',
                text: (el.textContent || '').trim().slice(0, 80),
                visible: el.offsetParent !== null,
                class: (el.className || '').slice(0, 40),
                w: el.getBoundingClientRect().width,
                h: el.getBoundingClientRect().height,
                y: el.getBoundingClientRect().y
            })).filter(e => e.visible && e.w > 0 && e.h > 0)
                .sort((a, b) => a.y - b.y);
        }''')
        
        print(f"\nAll input elements ({len(inputs)}):")
        for inp in inputs:
            print(f"  y={inp['y']:.0f} {inp['tag']:6s} type={inp['type']:12s} id={inp['id']:30s} name={inp['name']:25s} placeholder=\"{inp['placeholder']}\" text=\"{inp['text']}\" class={inp['class']}")
        
        # Also dump all visible text
        text = await page.evaluate('''() => {
            return Array.from(document.querySelectorAll('body *'))
                .filter(el => el.children.length === 0 && el.textContent.trim())
                .map(el => el.textContent.trim())
                .filter(t => t.length > 0 && t.length < 200)
                .slice(0, 50);
        }''')
        print(f"\nPage text content:")
        for t in text:
            print(f"  {t}")
            
        # Dump full page HTML around the form
        html = await page.evaluate('''() => {
            const form = document.querySelector('#createAccount') || document.querySelector('form') || document.body;
            return form.parentElement ? form.parentElement.innerHTML.slice(0, 5000) : document.body.innerHTML.slice(0, 5000);
        }''')
        print(f"\nForm HTML (around signup link):")
        print(html[:3000])
    
    await page.screenshot(path='/opt/render/reports/signup_final.png', full_page=True)
    await browser.close()
    await pw.stop()

asyncio.run(main())
