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

    await page.goto('https://www.genspark.ai/', wait_until='networkidle', timeout=60000)
    await asyncio.sleep(8)

    # Dump ALL text nodes and elements in header/nav
    js = """
    () => {
        const all = document.querySelectorAll('*');
        let results = [];
        for (const el of all) {
            const text = (el.textContent || '').trim();
            const tag = el.tagName;
            const rect = el.getBoundingClientRect();
            if (text.length > 0 && text.length < 100 && rect.width > 0 && rect.height > 0 && el.offsetParent !== null) {
                // Check if it has visible text (no hidden overflow trick)
                const style = window.getComputedStyle(el);
                if (style.overflow !== 'hidden' || parseInt(style.maxHeight) > 0) {
                    results.push({tag, text: text.slice(0, 60), cls: (el.className || '').slice(0, 60), id: el.id, x: rect.x, y: rect.y});
                }
            }
        }
        // Filter for likely header/nav elements (top of page)
        const topElements = results.filter(r => r.y < 100).sort((a, b) => a.x - b.x);
        return topElements.slice(0, 30);
    }
    """
    els = await page.evaluate(js)
    print('=== TOP OF PAGE (y < 100) TEXT ELEMENTS ===')
    for e in els:
        print(f'  {e["tag"]:6s} x={e["x"]:.0f} y={e["y"]:.0f} text="{e["text"]}" cls="{e["cls"]}"')

    # Also check the full HTML for auth-related content
    html = await page.content()
    for keyword in ['sign', 'login', 'auth', 'account', 'register', 'Log in', 'Sign in']:
        idx = html.lower().find(keyword.lower())
        if idx >= 0:
            snippet = html[max(0,idx-100):idx+100]
            print(f'\n  Found "{keyword}" at {idx}: ...{snippet}...')

    await page.screenshot(path='/opt/render/reports/probe_main_full.png', full_page=True)
    await browser.close()
    await pw.stop()

asyncio.run(probe())
