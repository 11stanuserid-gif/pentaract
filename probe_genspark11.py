#!/usr/bin/env python3
"""Try to directly interact with genspark's signup/login by looking at JS bundles"""
import asyncio
import re
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
    
    # Capture script content
    scripts_content = []
    
    async def capture_script(response):
        if response.url.endswith('.js') and 'genspark' in response.url:
            try:
                body = await response.text()
                scripts_content.append({"url": response.url, "body": body[:50000]})
            except:
                pass
    
    page.on("response", capture_script)
    
    await page.goto('https://www.genspark.ai/', wait_until='networkidle', timeout=60000)
    await asyncio.sleep(5)
    
    print(f"Captured {len(scripts_content)} script bundles")
    
    # Search for API endpoints in scripts
    for script in scripts_content[:5]:
        print(f"\n=== Script: {script['url'][:80]} ===")
        # Look for fetch/ajax calls
        for m in re.finditer(r'["\'](https?://[^"\']+)["\']', script['body']):
            url = m.group(1)
            if any(x in url for x in ['api', 'auth', 'sign', 'login', 'regis', 'user', 'account']):
                if 'google' not in url and 'facebook' not in url and 'gstatic' not in url:
                    print(f"  API URL: {url[:120]}")
        
        # Look for routes
        for m in re.finditer(r'["\'](/[a-zA-Z0-9_/.-]*)["\']', script['body']):
            path = m.group(1)
            if any(x in path for x in ['sign', 'login', 'regis', 'auth', 'account']):
                print(f"  Route: {path}")
    
    await browser.close()
    await pw.stop()

asyncio.run(probe())
