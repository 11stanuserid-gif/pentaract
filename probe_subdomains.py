#!/usr/bin/env python3
"""Try various approaches to find genspark signup"""
import asyncio
from playwright.async_api import async_playwright

async def try_paths():
    pw = await async_playwright().start()
    browser = await pw.chromium.launch(headless=True, args=['--no-sandbox', '--disable-blink-features=AutomationControlled'])
    context = await browser.new_context(
        viewport={'width': 1920, 'height': 1080},
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36'
    )
    await context.add_init_script("Object.defineProperty(navigator, 'webdriver', { get: () => undefined });")
    
    # Try genspark subdomains
    subdomains = [
        'https://app.genspark.ai',
        'https://auth.genspark.ai',
        'https://api.genspark.ai',
        'https://accounts.genspark.ai',
        'https://id.genspark.ai',
        'https://login.genspark.ai',
        'http://app.genspark.ai',
    ]
    
    for base_url in subdomains:
        page = await context.new_page()
        try:
            await page.goto(base_url, wait_until='domcontentloaded', timeout=15000)
            await asyncio.sleep(3)
            title = await page.title()
            content = await page.content()
            status = "OK" if len(content) > 500 else "EMPTY"
            print(f"\n{base_url}")
            print(f"  Title: {title}")
            print(f"  Status: {status}, length: {len(content)}")
            # Check for any forms
            forms = await page.evaluate('''() => document.querySelectorAll('form').length''')
            inputs = await page.evaluate('''() => document.querySelectorAll('input').length''')
            print(f"  Forms: {forms}, Inputs: {inputs}")
        except Exception as e:
            print(f"\n{base_url}\n  Error: {str(e)[:60]}")
        await page.close()
    
    await browser.close()
    await pw.stop()

asyncio.run(try_paths())
