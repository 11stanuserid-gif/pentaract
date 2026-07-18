#!/usr/bin/env python3
"""Simple captcha probe"""
import asyncio, base64, io, sys
from PIL import Image
from playwright.async_api import async_playwright

async def main():
    pw = await async_playwright().start()
    browser = await pw.chromium.launch(headless=True, args=['--no-sandbox'])
    context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
    page = await context.new_page()
    
    await page.goto('https://www.genspark.ai/login', wait_until='networkidle', timeout=60000)
    await asyncio.sleep(3)
    await page.locator('#createAccount').click()
    await asyncio.sleep(5)
    await page.fill('#email', 'testprobe@zoho.com')
    await asyncio.sleep(1)
    
    # Get captcha image src
    captcha_src = await page.evaluate('''() => {
        const img = document.getElementById('captchaControlChallengeCode-img');
        return img ? img.src : 'none';
    }''')
    print(f"Captcha src prefix: {captcha_src[:80]}...")
    
    if captcha_src.startswith('data:image'):
        header, encoded = captcha_src.split(',', 1)
        img_data = base64.b64decode(encoded)
        img = Image.open(io.BytesIO(img_data))
        print(f"Size: {img.size}, Mode: {img.mode}")
        img.save('/opt/render/reports/captcha.jpg')
        print("Saved captcha.jpg")
    
    # Check for audio captcha
    has_audio = await page.evaluate('''() => {
        const btn = document.getElementById('captchaControlChallengeCode-switchCaptchaBtn');
        return btn ? btn.offsetParent !== null : false;
    }''')
    print(f"Audio button visible: {has_audio}")
    
    await browser.close()
    await pw.stop()

asyncio.run(main())
