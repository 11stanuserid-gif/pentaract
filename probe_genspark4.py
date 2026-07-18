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

    # Dump EVERYTHING visible with y position
    js = """
    () => {
        const all = document.querySelectorAll('a, button, [role="button"], span, div');
        let results = [];
        for (const el of all) {
            const text = (el.textContent || '').trim();
            const tag = el.tagName;
            const rect = el.getBoundingClientRect();
            if (text.length > 0 && rect.width > 0 && rect.height > 0 && el.offsetParent !== null) {
                results.push({tag, text: text.slice(0, 100), x: rect.x, y: rect.y, w: rect.width, h: rect.height});
            }
        }
        return results
            .filter(r => r.text.length < 200)
            .sort((a, b) => a.y - b.y || a.x - b.x);
    }
    """
    els = await page.evaluate(js)
    print('=== ALL VISIBLE TEXT ELEMENTS (sorted by position) ===')
    for e in els[:100]:
        print(f'y={e["y"]:.0f} x={e["x"]:.0f} w={e["w"]:.0f}h={e["h"]:.0f} {e["tag"]:6s} "{e["text"][:80]}"')

    print(f'\n... total {len(els)} elements')

    await browser.close()
    await pw.stop()

asyncio.run(probe())
