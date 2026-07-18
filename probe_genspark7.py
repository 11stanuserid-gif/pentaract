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

    # Try clicking on "New" in the sidebar
    print("=== Trying to click 'New' ===")
    try:
        new_btn = await page.query_selector('text=New')
        if new_btn:
            print(f"Found 'New' button, visible: {await new_btn.is_visible()}")
            await new_btn.click()
            await asyncio.sleep(3)
            print(f"URL after click: {page.url}")
    except Exception as e:
        print(f"Error clicking 'New': {e}")

    # Check what's visible now
    html = await page.content()
    print(f"Page length: {len(html)}")

    # Look for modal/dialog elements
    modals = await page.evaluate('''() => {
        const dialogs = document.querySelectorAll('[role="dialog"], .modal, .overlay, [class*="modal"], [class*="dialog"]');
        return Array.from(dialogs).map(d => ({
            tag: d.tagName,
            id: d.id,
            cls: (d.className || '').slice(0, 100),
            visible: d.offsetParent !== null
        }));
    }''')
    print(f"Modals/dialogs: {len(modals)}")
    for m in modals:
        if m['visible']:
            print(f"  Visible modal: {m['tag']} id={m['id']} cls={m['cls']}")

    # Also try to look for login/signup buttons more broadly
    await page.screenshot(path='/opt/render/reports/probe_after_new.png', full_page=True)

    # Check all visible text again
    all_text = await page.evaluate('''() => {
        const all = document.querySelectorAll('*');
        return Array.from(all)
            .filter(el => el.offsetParent !== null && el.textContent.trim())
            .map(el => ({
                tag: el.tagName,
                text: el.textContent.trim().slice(0, 100),
                y: el.getBoundingClientRect().y
            }))
            .filter(el => el.y >= 0 && el.y < 120 && el.text.length < 50)
            .sort((a, b) => a.y - b.y);
    }''')
    print(f"\nTop-of-page visible text elements:")
    for t in all_text[:20]:
        print(f"  y={t['y']:.0f} {t['tag']:6s} \"{t['text']}\"")

    await browser.close()
    await pw.stop()

asyncio.run(probe())
