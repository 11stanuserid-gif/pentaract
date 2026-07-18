#!/usr/bin/env python3
"""Try to trigger signup flow on genspark by using a feature"""
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
    
    # Monitor all responses to find API endpoints
    responses = []
    page.on("response", lambda resp: responses.append({"url": resp.url, "status": resp.status, "type": resp.request.resource_type}))
    
    await page.goto('https://www.genspark.ai/', wait_until='networkidle', timeout=60000)
    await asyncio.sleep(5)
    
    # Try to find any input/textarea on the page - the AI chat input might trigger signup
    textareas = await page.query_selector_all('textarea, [contenteditable="true"], input[type="text"]')
    print(f"Found {len(textareas)} text inputs")
    
    # Try clicking on the main page area to see if anything happens
    await page.click('body', position={'x': 500, 'y': 200})
    await asyncio.sleep(2)
    
    # Check for any iframes (Google One Tap)
    iframes = await page.query_selector_all('iframe')
    print(f"Found {len(iframes)} iframes")
    for i, f in enumerate(iframes):
        src = await f.get_attribute('src')
        print(f"  iframe {i}: {src[:120]}")
    
    # Look for all API responses
    api_calls = [r for r in responses if '/api/' in r['url'] or r['type'] in ['xhr', 'fetch']]
    print(f"\n=== API calls ({len(api_calls)}) ===")
    for r in api_calls[:20]:
        print(f"  {r['status']} {r['type']:12s} {r['url'][:120]}")
    
    # Check page HTML for any signup/login forms that might be dynamically rendered
    # Look for specific selectors
    for sel in ['form', '[class*="login"]', '[class*="signup"]', '[class*="auth"]', '#login', '#signup']:
        els = await page.query_selector_all(sel)
        for el in els:
            visible = await el.is_visible()
            print(f"  Selector '{sel}': found {len(els)}, visible={visible}")
    
    await page.screenshot(path='/opt/render/reports/probe_final.png', full_page=True)
    
    # Now try to look at the JavaScript bundle for API endpoints
    print("\n=== Page source for api/signup endpoints ===")
    content = await page.content()
    import re
    for m in re.finditer(r'["\'](/api/[^"\']+)["\']', content):
        path = m.group(1)
        if any(x in path.lower() for x in ['auth', 'sign', 'login', 'regis', 'account', 'user']):
            print(f"  Found: {path}")
    
    await browser.close()
    await pw.stop()

asyncio.run(probe())
