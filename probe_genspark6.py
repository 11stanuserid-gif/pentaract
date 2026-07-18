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
    await asyncio.sleep(5)

    # Check the current URL again - sometimes Cloudflare redirects
    print(f'URL: {page.url}')
    print(f'Title: {await page.title()}')

    # Scroll to top
    await page.evaluate("window.scrollTo(0, 0)")
    await asyncio.sleep(1)

    # Get all buttons and A tags
    all_els = await page.evaluate('''() => {
        const all = document.querySelectorAll('a, button, [role="button"], input, [onclick]');
        return Array.from(all).map(el => ({
            tag: el.tagName,
            id: el.id,
            type: el.type || '',
            text: (el.textContent || '').trim().slice(0, 80),
            href: el.href || '',
            cls: (el.className || '').slice(0, 100),
            visible: el.offsetParent !== null && el.getBoundingClientRect().width > 0,
            rect: el.getBoundingClientRect()
        }));
    }''')

    print(f'\nTotal elements found: {len(all_els)}')
    
    # Filter visible ones
    visible = [e for e in all_els if e['visible']]
    print(f'Visible: {len(visible)}')
    
    # Print them sorted by position
    visible.sort(key=lambda e: (e['rect']['y'], e['rect']['x']))
    for e in visible:
        if e['text'] or e['id']:
            print(f'  y={e["rect"]["y"]:.0f} x={e["rect"]["x"]:.0f} {e["tag"]:6s} type={e["type"]:12s} id={e["id"]:20s} text="{e["text"][:60]}"')

    # Also look at the full HTML for auth patterns
    html = await page.content()
    import re
    for pattern in ['sign.?in', 'sign.?up', 'log.?in', 'register', 'account', 'auth', 'login', 'Sign In', 'Sign Up', 'Log In']:
        matches = [(m.start(), html[max(0,m.start()-50):m.end()+50]) for m in re.finditer(pattern, html, re.IGNORECASE)]
        if matches:
            print(f'\n--- Pattern: "{pattern}" ({len(matches)} matches) ---')
            for pos, ctx in matches[:3]:
                print(f'  at {pos}: ...{ctx}...')

    await page.screenshot(path='/opt/render/reports/probe_main_detailed.png', full_page=True)
    await browser.close()
    await pw.stop()

asyncio.run(probe())
