#!/usr/bin/env python3
"""Probe genspark.ai thoroughly"""
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
    
    await page.goto('https://www.genspark.ai/', wait_until='networkidle', timeout=60000)
    await asyncio.sleep(5)
    
    # Find ANY input elements
    inputs = await page.evaluate('''() => {
        const all = document.querySelectorAll('input, textarea, [contenteditable="true"]');
        return Array.from(all).map(el => ({
            tag: el.tagName,
            type: el.type || '',
            id: el.id || '',
            name: el.name || '',
            placeholder: el.placeholder || '',
            cls: (el.className || '').slice(0, 60),
            visible: el.offsetParent !== null,
            w: el.getBoundingClientRect().width,
            h: el.getBoundingClientRect().height,
            x: el.getBoundingClientRect().x,
            y: el.getBoundingClientRect().y
        }));
    }''')
    print(f"=== INPUT ELEMENTS ({len(inputs)}) ===")
    for inp in inputs:
        print(f"  {inp['tag']:8s} type={inp['type']:15s} id={inp['id']:20s} visible={inp['visible']} pos=({inp['x']:.0f},{inp['y']:.0f}) size={inp['w']:.0f}x{inp['h']:.0f}")
        if inp['placeholder']:
            print(f"    placeholder: {inp['placeholder']}")

    # Find iframes
    iframes = await page.evaluate('''() => {
        return Array.from(document.querySelectorAll('iframe')).map(f => f.src || '').filter(s => s);
    }''')
    print(f"\n=== IFRAMES ({len(iframes)}) ===")
    for src in iframes:
        print(f"  {src[:150]}")

    # Check what buttons exist
    buttons = await page.evaluate('''() => {
        const all = document.querySelectorAll('button, [role="button"], a[href]');
        return Array.from(all).map(el => ({
            tag: el.tagName,
            text: (el.textContent || '').trim().slice(0, 60),
            cls: (el.className || '').slice(0, 80),
            visible: el.offsetParent !== null,
            w: el.getBoundingClientRect().width
        })).filter(e => e.visible && e.w > 0 && e.text);
    }''')
    # Filter to unique text content
    seen = set()
    print(f"\n=== ALL VISIBLE CLICKABLE TEXT (y sorted) ===")
    for b in buttons:
        if b['text'] not in seen:
            seen.add(b['text'])
            print(f"  \"{b['text'][:50]}\"")

    await page.screenshot(path='/opt/render/reports/probe_final.png', full_page=True)
    await browser.close()
    await pw.stop()

asyncio.run(probe())
