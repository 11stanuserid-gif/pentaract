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
    
    # Listen for all requests
    page = await context.new_page()
    
    # Monitor network requests
    requests = []
    page.on("request", lambda req: requests.append({"url": req.url, "method": req.method, "type": req.resource_type}))
    
    await page.goto('https://www.genspark.ai/', wait_until='networkidle', timeout=60000)
    await asyncio.sleep(8)

    # Check auth-related network calls
    auth_urls = [r for r in requests if any(x in r['url'] for x in ['auth', 'login', 'sign', 'google', 'token', 'session', 'account'])]
    print("=== Auth-related network calls ===")
    for r in auth_urls[:20]:
        print(f"  {r['method']} {r['type']:12s} {r['url'][:120]}")

    # Check localStorage and sessionStorage for auth data
    storage = await page.evaluate('''() => {
        const ls = {};
        for (let i = 0; i < localStorage.length; i++) {
            const k = localStorage.key(i);
            ls[k] = localStorage.getItem(k).slice(0, 100);
        }
        const ss = {};
        for (let i = 0; i < sessionStorage.length; i++) {
            const k = sessionStorage.key(i);
            ss[k] = sessionStorage.getItem(k).slice(0, 100);
        }
        return {localStorage: ls, sessionStorage: ss};
    }''')
    print(f"\n=== localStorage ===")
    for k, v in storage['localStorage'].items():
        print(f"  {k}: {v}")
    print(f"\n=== sessionStorage ===")
    for k, v in storage['sessionStorage'].items():
        print(f"  {k}: {v}")

    # Try to get cookies
    cookies = await context.cookies()
    print(f"\n=== Cookies ({len(cookies)}) ===")
    for c in cookies:
        print(f"  {c['name']}: {c['value'][:60]}")

    await page.screenshot(path='/opt/render/reports/probe_network.png', full_page=True)
    await browser.close()
    await pw.stop()

asyncio.run(probe())
