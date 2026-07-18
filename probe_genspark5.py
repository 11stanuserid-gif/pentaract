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
    
    # Try different auth paths
    paths = ['/login', '/signin', '/auth', '/sign-up', '/register', '/auth/login', '/en/login']
    
    for path in paths:
        page = await context.new_page()
        try:
            url = f'https://www.genspark.ai{path}'
            await page.goto(url, wait_until='domcontentloaded', timeout=30000)
            await asyncio.sleep(3)
            title = await page.title()
            content_preview = (await page.content())[:500]
            print(f'\n=== {url} ===')
            print(f'Title: {title}')
            # Check for 404
            if '404' in content_preview[:1000]:
                print('-> 404 Not Found')
            elif 'login' in content_preview.lower() or 'sign' in content_preview.lower():
                print(f'-> Possible auth page! Content: {content_preview[:300]}')
            else:
                print(f'-> Something else')
            await page.screenshot(path=f'/opt/render/reports/probe_{path.replace("/","_")}.png', full_page=True)
        except Exception as e:
            print(f'\n=== {url} === Error: {e}')
        await page.close()
    
    await browser.close()
    await pw.stop()

asyncio.run(probe())
