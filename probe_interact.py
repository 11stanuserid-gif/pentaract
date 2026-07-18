#!/usr/bin/env python3
"""Interact with genspark sidebar to find signup flow"""
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
    
    # Monitor URL changes
    urls = []
    page.on("framenavigated", lambda frame: urls.append(frame.url))
    
    await page.goto('https://www.genspark.ai/', wait_until='networkidle', timeout=60000)
    await asyncio.sleep(5)
    
    print(f"Initial URL: {page.url}")
    
    # Try clicking on each sidebar item
    for item in ['New', 'Home', 'Skills', 'Claw', 'Drive', 'More']:
        try:
            btn = page.locator(f'text={item}').first
            if await btn.is_visible():
                await btn.click()
                await asyncio.sleep(2)
                print(f"Clicked '{item}' -> URL: {page.url}")
        except Exception as e:
            print(f"Click '{item}' failed: {str(e)[:60]}")
    
    # Check the final state
    print(f"\nFinal URL: {page.url}")
    print(f"All navigations: {urls[:10]}")
    
    # Check if any modal appeared
    modals = await page.evaluate('''() => {
        const all = document.querySelectorAll('*');
        return Array.from(all).filter(el => {
            const text = el.textContent.toLowerCase();
            return el.offsetParent !== null && 
                   el.getBoundingClientRect().width > 0 &&
                   (text.includes('sign') || text.includes('login') || text.includes('register') || 
                    text.includes('email') || text.includes('password') || text.includes('account'));
        }).map(el => ({
            tag: el.tagName,
            text: el.textContent.trim().slice(0, 100),
            cls: (el.className || '').slice(0, 60),
            x: el.getBoundingClientRect().x,
            y: el.getBoundingClientRect().y,
            w: el.getBoundingClientRect().width,
            h: el.getBoundingClientRect().height
        })).filter(e => e.w > 0 && e.h > 0);
    }''')
    
    print(f"\nAuth-related visible elements: {len(modals)}")
    for m in modals:
        print(f"  y={m['y']:.0f} \"{m['text'][:80]}\" cls={m['cls']}")
    
    await page.screenshot(path='/opt/render/reports/probe_interact.png', full_page=True)
    await browser.close()
    await pw.stop()

asyncio.run(probe())
