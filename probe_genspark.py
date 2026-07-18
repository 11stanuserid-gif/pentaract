#!/usr/bin/env python3
import asyncio
from playwright.async_api import async_playwright

async def probe():
    pw = await async_playwright().start()
    browser = await pw.chromium.launch(headless=True, args=['--no-sandbox', '--disable-blink-features=AutomationControlled'])
    context = await browser.new_context(
        viewport={'width': 1920, 'height': 1080},
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36'
    )
    await context.add_init_script("Object.defineProperty(navigator, 'webdriver', { get: () => undefined });")
    page = await context.new_page()
    await page.goto('https://www.genspark.ai/signup', wait_until='networkidle', timeout=60000)
    await asyncio.sleep(5)
    
    # Take full page screenshot
    await page.screenshot(path='/opt/render/reports/probe_signup.png', full_page=True)
    
    # Dump all interactive elements
    js_code = """
    () => {
        const els = document.querySelectorAll('input, button, a[href], [role="button"], [tabindex]');
        return Array.from(els).slice(0, 50).map(el => ({
            tag: el.tagName,
            type: el.type || '',
            name: el.name || '',
            id: el.id || '',
            placeholder: el.placeholder || '',
            text: (el.textContent || '').trim().slice(0, 60),
            visible: el.offsetParent !== null,
            w: el.getBoundingClientRect().width
        }));
    }
    """
    elements = await page.evaluate(js_code)
    
    print('=== INTERACTIVE ELEMENTS ===')
    for e in elements:
        if e['visible'] and e['w'] > 0:
            print(f'{e["tag"]} type={e["type"]} name={e["name"]} id={e["id"]}')
            if e['text']: print(f'  text: {e["text"]}')
            if e['placeholder']: print(f'  placeholder: {e["placeholder"]}')
    
    print(f'\nFinal URL: {page.url}')
    print(f'Title: {await page.title()}')
    
    # Also dump body HTML
    body_html = await page.evaluate("document.body.innerHTML.substring(0, 3000)")
    print(f'\n=== BODY HTML (first 3000 chars) ===')
    print(body_html)
    
    await browser.close()
    await pw.stop()

asyncio.run(probe())
