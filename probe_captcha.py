#!/usr/bin/env python3
"""Probe the CAPTCHA mechanism on genspark Azure B2C signup"""
import asyncio
from playwright.async_api import async_playwright

async def main():
    pw = await async_playwright().start()
    browser = await pw.chromium.launch(headless=True, args=['--no-sandbox', '--disable-blink-features=AutomationControlled'])
    context = await browser.new_context(
        viewport={'width': 1920, 'height': 1080},
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    )
    await context.add_init_script("Object.defineProperty(navigator, 'webdriver', { get: () => undefined });")
    
    page = await context.new_page()
    
    await page.goto('https://www.genspark.ai/login', wait_until='networkidle', timeout=60000)
    await asyncio.sleep(3)
    
    # Click "Sign up now"
    await page.locator('#createAccount').click()
    await asyncio.sleep(5)
    
    # Enter email first
    await page.fill('#email', 'testprobe999@zoho.com')
    await asyncio.sleep(1)
    
    # Now look at the captcha element
    captcha_info = await page.evaluate('''() => {
        const generateBtn = document.getElementById('captchaControlChallengeCode-generateCaptchaBtn');
        const img = document.querySelector('#captchaControlChallengeCode + img, .captchaImage img, img[alt*="captcha"], img[alt*="Captcha"], img[id*="captcha"]');
        const captchaContainer = document.querySelector('[id*="captcha"], .captcha, [class*="captcha"]');
        
        // Look for captcha image
        const allImages = Array.from(document.querySelectorAll('img')).map(img => ({
            src: img.src.slice(0, 200),
            alt: img.alt,
            id: img.id,
            className: (img.className || '').slice(0, 40),
            visible: img.offsetParent !== null,
            w: img.width,
            h: img.height,
            rect: img.getBoundingClientRect()
        }));
        
        return {
            hasGenerateBtn: generateBtn !== null,
            generateBtnVisible: generateBtn ? generateBtn.offsetParent !== null : false,
            directImg: img ? {src: img.src.slice(0,200), id: img.id, alt: img.alt} : null,
            allImages: allImages,
            captchaContainer: captchaContainer ? captchaContainer.outerHTML.slice(0, 500) : 'not found'
        };
    }''')
    
    print("Captcha info:")
    import json
    print(json.dumps(captcha_info, indent=2, default=str))
    
    # Also check what happens when we click generate
    if captcha_info.get('hasGenerateBtn'):
        print("\nClicking generate captcha button...")
        await page.click('#captchaControlChallengeCode-generateCaptchaBtn')
        await asyncio.sleep(3)
        
        # Check for new image
        new_info = await page.evaluate('''() => {
            const allImages = Array.from(document.querySelectorAll('img')).map(img => ({
                src: img.src.slice(0, 300),
                alt: img.alt,
                id: img.id,
                className: (img.className || '').slice(0, 40),
                visible: img.offsetParent !== null
            }));
            return {allImages};
        }''')
        print("After generate click:", json.dumps(new_info, indent=2))
    
    await page.screenshot(path='/opt/render/reports/captcha_probe.png', full_page=True)
    await browser.close()
    await pw.stop()

asyncio.run(main())
