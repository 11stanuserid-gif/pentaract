#!/usr/bin/env python3
"""Check genspark login page flow"""
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
    
    # Try /login page
    await page.goto('https://www.genspark.ai/login', wait_until='networkidle', timeout=60000)
    await asyncio.sleep(5)
    
    print(f"Login URL: {page.url}")
    print(f"Login Title: {await page.title()}")
    
    # Dump all interactive elements
    els = await page.evaluate('''() => {
        const all = document.querySelectorAll('a, button, input, [role="button"], form');
        return Array.from(all).map(el => ({
            tag: el.tagName,
            type: el.type || '',
            text: (el.textContent || '').trim().slice(0, 80),
            href: el.href || '',
            visible: el.offsetParent !== null,
            w: el.getBoundingClientRect().width,
            h: el.getBoundingClientRect().height,
            x: el.getBoundingClientRect().x,
            y: el.getBoundingClientRect().y
        })).filter(e => e.visible && e.w > 0 && e.h > 0);
    }''')
    
    print(f"\nVisible elements: {len(els)}")
    for e in els:
        if e['text'] or e['href']:
            print(f"  y={e['y']:.0f} {e['tag']:6s} type={e['type']:12s} text=\"{e['text'][:50]}\" href=\"{e['href'][:80]}\"")
    
    await page.screenshot(path='/opt/render/reports/probe_login.png', full_page=True)
    
    # Also check for any iframe overlays
    iframes = await page.evaluate('''() => {
        return Array.from(document.querySelectorAll('iframe')).map(f => f.src || '').filter(s => s);
    }''')
    print(f"\nIframes: {len(iframes)}")
    for s in iframes:
        print(f"  {s[:150]}")
    
    await browser.close()
    await pw.stop()

asyncio.run(probe())
