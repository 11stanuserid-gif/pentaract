#!/usr/bin/env python3
"""Detailed captcha probe - save image and check audio option"""
import asyncio, base64, io, json
from PIL import Image
from playwright.async_api import async_playwright

async def main():
    pw = await async_playwright().start()
    browser = await pw.chromium.launch(headless=True, args=['--no-sandbox', '--disable-blink-features=AutomationControlled'])
    context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
    await context.add_init_script("Object.defineProperty(navigator, 'webdriver', { get: () => undefined });")
    
    page = await context.new_page()
    await page.goto('https://www.genspark.ai/login', wait_until='networkidle', timeout=60000)
    await asyncio.sleep(3)
    await page.locator('#createAccount').click()
    await asyncio.sleep(5)
    await page.fill('#email', 'testprobe@zoho.com')
    await asyncio.sleep(1)
    
    # Get captcha image data
    captcha_data = await page.evaluate('''() => {
        const img = document.getElementById('captchaControlChallengeCode-img');
        return img ? img.src : null;
    }''')
    
    if captcha_data and captcha_data.startswith('data:image'):
        # Save the captcha image
        header, encoded = captcha_data.split(',', 1)
        img_data = base64.b64decode(encoded)
        with open('/opt/render/reports/captcha.jpg', 'wb') as f:
            f.write(img_data)
        print(f"Saved captcha image: {len(img_data)} bytes")
        
        # Check dimensions with PIL
        img = Image.open(io.BytesIO(img_data))
        print(f"Captcha size: {img.size}, mode: {img.mode}")
        img.save('/opt/render/reports/captcha_debug.png')
    
    # Check audio captcha option
    audio_info = await page.evaluate('''() => {
        const switchBtn = document.getElementById('captchaControlChallengeCode-switchCaptchaBtn');
        if (!switchBtn) return {found: false};
        return {
            found: true,
            html: switchBtn.outerHTML,
            onclick: switchBtn.getAttribute('onclick') || '',
            visible: switchBtn.offsetParent !== null
        };
    }''')
    print(f"Audio button: {json.dumps(audio_info, indent=2)}")
    
    # Click switch and check
    if audio_info.get('found') and audio_info.get('visible'):
        print("Clicking audio switch...")
        await page.click('#captchaControlChallengeCode-switchCaptchaBtn')
        await asyncio.sleep(3)
        
        # Check for audio element
        audio_elem = await page.evaluate('''() => {
            const audio = document.querySelector('audio');
            const source = document.querySelector('source');
            const links = Array.from(document.querySelectorAll('a')).filter(a => a.href.includes('.wav') || a.href.includes('.mp3'));
            const imgs = Array.from(document.querySelectorAll('img')).filter(img => img.src.includes('captcha'));
            return {
                audio: audio ? audio.outerHTML.slice(0, 500) : null,
                source: source ? source.src : null,
                links: links.map(l => l.href),
                imgs: imgs.map(i => ({src: i.src.slice(0, 200), id: i.id}))
            };
        }''')
        print(f"After audio switch: {json.dumps(audio_elem, indent=2)}")
        await page.screenshot(path='/opt/render/reports/captcha_audio.png', full_page=True)
    
    await browser.close()
    await pw.stop()

asyncio.run(main())
