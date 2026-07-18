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

    # Go to main page
    await page.goto('https://www.genspark.ai/', wait_until='networkidle', timeout=60000)
    await asyncio.sleep(5)

    print(f'URL: {page.url}')
    print(f'Title: {await page.title()}')

    # Get all links and buttons
    js = """
    () => {
        const els = document.querySelectorAll('a, button, [role="button"]');
        return Array.from(els).slice(0, 80).map(el => ({
            tag: el.tagName,
            id: el.id || '',
            text: (el.textContent || '').trim().slice(0, 80),
            href: el.href || '',
            class: (el.className || '').slice(0, 120),
            visible: el.offsetParent !== null,
            w: el.getBoundingClientRect().width
        })).filter(e => e.visible && e.w > 0);
    }
    """
    els = await page.evaluate(js)
    print('\n=== ALL VISIBLE BUTTONS & LINKS ===')
    for e in els:
        print(f'{e["tag"]:6s} text="{e["text"]:40s}" href="{e["href"][:80]}" cls="{e["class"][:80]}"')

    await page.screenshot(path='/opt/render/reports/probe_main.png', full_page=True)

    await browser.close()
    await pw.stop()

asyncio.run(probe())
