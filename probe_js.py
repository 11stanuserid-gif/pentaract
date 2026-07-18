#!/usr/bin/env python3
"""Download and analyze genspark JS bundles for auth API endpoints"""
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
    
    # Collect all JS responses
    js_bundles = []
    
    async def on_response(response):
        if response.url.endswith('.js') and 'cdn-static.genspark.ai' in response.url:
            try:
                body = await response.text()
                js_bundles.append({"url": response.url, "body": body})
            except:
                pass
    
    page.on("response", on_response)
    
    await page.goto('https://www.genspark.ai/', wait_until='networkidle', timeout=60000)
    await asyncio.sleep(5)
    
    print(f"Collected {len(js_bundles)} JS bundles")
    
    # Search for auth API endpoints
    all_text = ""
    for bundle in js_bundles:
        all_text += bundle["body"]
    
    print(f"Total JS size: {len(all_text)} chars")
    
    # Find API routes
    patterns = [
        r'["\'](/api/[a-zA-Z0-9_/.-]*)["\']',
        r'["\'](https?://[a-zA-Z0-9.-]*genspark[a-zA-Z0-9.-]*/api/[a-zA-Z0-9_/.-]*)["\']',
        r'["\'](/v1/[a-zA-Z0-9_/.-]*)["\']',
        r'["\'](/v2/[a-zA-Z0-9_/.-]*)["\']',
        r'url:\s*["\'](/[a-zA-Z0-9_/.-]*)["\']',
        r'path:\s*["\'](/[a-zA-Z0-9_/.-]*)["\']',
    ]
    
    auth_endpoints = set()
    for pattern in patterns:
        for m in re.finditer(pattern, all_text):
            path = m.group(1)
            if any(kw in path.lower() for kw in ['auth', 'sign', 'login', 'regis', 'user', 'account', 'token', 'session', 'oauth', 'password']):
                if 'google' not in path and 'facebook' not in path:
                    auth_endpoints.add(path)
    
    print(f"\n=== AUTH ENDPOINTS ({len(auth_endpoints)}) ===")
    for ep in sorted(auth_endpoints):
        print(f"  {ep}")
    
    # Also find the main entry script URLs
    print(f"\n=== JS Bundle URLs ===")
    for b in js_bundles:
        print(f"  {b['url']}")
    
    await browser.close()
    await pw.stop()

asyncio.run(probe())
