#!/usr/bin/env python3
"""
Genspark.ai Signup Bot v3
Targeted Azure B2C signup with email verification and captcha handling.
"""

import asyncio
import base64
import io
import json
import logging
import random
import re
import string
import sys
import time
from datetime import datetime
from io import BytesIO
from typing import Dict, List, Optional, Tuple

import aiohttp
from PIL import Image, ImageFilter, ImageEnhance, ImageOps

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("genspark-signup-v3")

# ============================================================
# Identity Generator — ensures truly unique emails
# ============================================================

FIRST_NAMES = [
    "Aarav", "Vivaan", "Aditya", "Vihaan", "Arjun", "Rohan", "Krishna",
    "Ishaan", "Rahul", "Amit", "Nikhil", "Siddharth", "Dev", "Kabir",
    "Aryan", "Farhan", "Imran", "Zayed", "Rehan", "Vijay", "Deepak",
    "Suresh", "Gaurav", "Ankit", "Praveen", "Sandeep", "Ravi", "Ganesh",
    "Diya", "Saanvi", "Ananya", "Navya", "Myra", "Pari", "Kavya", "Sara",
    "Neha", "Priya", "Sneha", "Pooja", "Riya", "Tanya", "Anika", "Zara",
    "Ishita", "Meera", "Nisha", "Simran", "Divya", "Shreya", "Fatima",
    "Ayesha", "Zainab", "Maryam", "Hafsa", "Aditi", "Isha", "Sonia",
    "Anjali", "Priyanka", "Deepika", "Katrina", "Alia", "Shraddha",
]

LAST_NAMES = [
    "Sharma", "Kumar", "Singh", "Patel", "Gupta", "Reddy", "Nair",
    "Iyer", "Joshi", "Mehta", "Desai", "Shah", "Verma", "Rao",
    "Malhotra", "Chopra", "Banerjee", "Das", "Mishra", "Agarwal",
    "Yadav", "Thakur", "Pandey", "Tiwari", "Bhat", "Menon",
    "Pillai", "Naik", "Kamat", "Shetty", "Kapoor", "Khanna",
    "Chauhan", "Rajput", "Bajaj", "Srinivasan", "Murthy", "Kulkarni",
    "Deshpande", "Chakraborty", "Mukherjee", "Bhattacharya",
]

EMAIL_DOMAINS = [
    "gmail.com", "yahoo.com", "outlook.com", "hotmail.com",
    "rediffmail.com", "icloud.com", "protonmail.com",
    "zoho.com", "yandex.com", "gmx.com",
    "fastmail.com", "aol.com", "live.com", "msn.com",
    "tutanota.com", "hushmail.com", "keemail.me",
    "mail.com", "inbox.com", "dispostable.com",
]


class IdentityGenerator:
    def __init__(self):
        self._used_emails: set = set()
        self._used_names: set = set()
        self._domain_index = 0

    def _next_domain(self) -> str:
        domain = EMAIL_DOMAINS[self._domain_index % len(EMAIL_DOMAINS)]
        self._domain_index += 1
        return domain

    def generate_identity(self) -> Dict:
        first = random.choice(FIRST_NAMES)
        last = random.choice(LAST_NAMES)
        full_name = f"{first} {last}"
        while full_name in self._used_names:
            first = random.choice(FIRST_NAMES)
            last = random.choice(LAST_NAMES)
            full_name = f"{first} {last}"
        self._used_names.add(full_name)

        email = None
        for _ in range(50):
            ts = int(time.time() * 1000000) % 100000000
            rnd = random.randint(10000, 99999)
            domain = self._next_domain()
            candidate = f"u{ts}_{rnd}@{domain}"
            if candidate not in self._used_emails:
                email = candidate
                break
        if not email:
            email = f"user_{random.randint(10000000, 99999999)}_{int(time.time()*1000000)}@{EMAIL_DOMAINS[0]}"
        self._used_emails.add(email)

        pw_len = random.randint(10, 14)
        password = ''.join(random.choices(string.ascii_lowercase, k=pw_len))

        return {
            "first_name": first,
            "last_name": last,
            "full_name": full_name,
            "email": email,
            "password": password,
        }


# ============================================================
# Temp Email Service
# ============================================================

class TempMailService:
    BASE_URL = "https://api.mail.tm"

    @staticmethod
    async def create_email() -> Optional[Dict]:
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(f"{TempMailService.BASE_URL}/domains", timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    domains_data = await resp.json()
                    domains = [d["domain"] for d in domains_data.get("hydra:member", []) if d.get("isActive", True)]
            except Exception:
                domains = ["mail.tm", "trialos.dev", "habibur.dev"]
            if not domains:
                domains = ["mail.tm"]
            random.shuffle(domains)

            for domain in domains[:3]:
                uid = str(random.randint(100000, 9999999))
                username = f"u{uid}_{int(time.time() * 1000) % 100000}"
                email = f"{username}@{domain}"
                password = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
                try:
                    async with session.post(
                        f"{TempMailService.BASE_URL}/accounts",
                        json={"address": email, "password": password},
                        timeout=aiohttp.ClientTimeout(total=10),
                    ) as resp:
                        if resp.status not in (200, 201):
                            continue
                        account = await resp.json()
                    async with session.post(
                        f"{TempMailService.BASE_URL}/token",
                        json={"address": email, "password": password},
                        timeout=aiohttp.ClientTimeout(total=10),
                    ) as resp:
                        if resp.status != 200:
                            continue
                        token_data = await resp.json()
                    return {"email": email, "password": password, "token": token_data["token"], "id": token_data.get("id", account.get("id", ""))}
                except Exception as e:
                    logger.warning(f"Temp email failed for {domain}: {e}")
                    continue
            return None

    @staticmethod
    async def check_inbox(token: str, timeout: int = 120, poll_interval: int = 5) -> Optional[Dict]:
        logger.info(f"Waiting for email (timeout: {timeout}s)...")
        start = time.time()
        seen = set()
        async with aiohttp.ClientSession() as session:
            while time.time() - start < timeout:
                try:
                    async with session.get(
                        f"{TempMailService.BASE_URL}/messages",
                        headers={"Authorization": f"Bearer {token}"},
                        timeout=aiohttp.ClientTimeout(total=10),
                    ) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            messages = data.get("hydra:member", [])
                            for msg in messages:
                                msg_id = msg.get("id")
                                if msg_id and msg_id not in seen:
                                    seen.add(msg_id)
                                    subject = (msg.get("subject") or "").lower()
                                    from_addr = (msg.get("from", {}) or {}).get("address", "").lower()
                                    if any(kw in subject for kw in ["verify", "code", "verification", "confirm", "welcome", "otp"]):
                                        async with session.get(
                                            f"{TempMailService.BASE_URL}/messages/{msg_id}",
                                            headers={"Authorization": f"Bearer {token}"},
                                            timeout=aiohttp.ClientTimeout(total=10),
                                        ) as full_resp:
                                            if full_resp.status == 200:
                                                full_msg = await full_resp.json()
                                                return {
                                                    "subject": msg.get("subject"),
                                                    "from": from_addr,
                                                    "text": full_msg.get("text", ""),
                                                    "html": full_msg.get("html", ""),
                                                }
                except Exception as e:
                    logger.warning(f"Inbox check error: {e}")
                await asyncio.sleep(poll_interval)
        logger.warning("Timeout waiting for email")
        return None

    @staticmethod
    def extract_code_or_link(message: Dict) -> Optional[str]:
        content = message.get("html", "") or message.get("text", "")
        # Look for numeric verification codes
        patterns = [
            r'(?:verification|code|confirm|otp)\s*[:\s]\s*(\d{4,8})',
            r'>(\d{4,8})<',
            r'(\d{4,8})\s*(?:is|code|verification)',
            r'\b(\d{6})\b',
        ]
        for p in patterns:
            m = re.search(p, content, re.IGNORECASE)
            if m:
                return m.group(1)
        # Look for verification links
        links = re.findall(r'href=["\'](https?://[^"\']*?(?:verify|confirm|activate)[^"\']*?)["\']', content, re.IGNORECASE)
        if links:
            return links[0].replace("&amp;", "&")
        return None


# ============================================================
# CAPTCHA Solver for Azure B2C Visual Captcha
# ============================================================

class B2CCaptchaSolver:
    @staticmethod
    async def solve_via_ocr_space(page) -> Optional[str]:
        try:
            captcha_src = await page.evaluate("""
                () => {
                    const img = document.getElementById('captchaControlChallengeCode-img');
                    return img ? img.src : null;
                }
            """)
            if not captcha_src or not captcha_src.startswith('data:image'):
                logger.warning("No captcha image found")
                return None

            header, encoded = captcha_src.split(',', 1)
            img_data = base64.b64decode(encoded)

            with open(f'/opt/render/reports/captcha_{int(time.time())}.jpg', 'wb') as f:
                f.write(img_data)

            img = Image.open(BytesIO(img_data))
            gray = img.convert('L')
            enhancer = ImageEnhance.Contrast(gray)
            high_contrast = enhancer.enhance(3.0)
            sharp = high_contrast.filter(ImageFilter.SHARPEN).filter(ImageFilter.SHARPEN)
            threshold = 128
            binary = sharp.point(lambda p: 255 if p > threshold else 0)
            binary_inv = ImageOps.invert(binary)

            processed_buf = BytesIO()
            binary_inv.save(processed_buf, format='PNG')
            processed_data = processed_buf.getvalue()

            result = await B2CCaptchaSolver._ocr_space_api(processed_data)
            if result:
                return result

            original_buf = BytesIO()
            img.save(original_buf, format='PNG')
            result = await B2CCaptchaSolver._ocr_space_api(original_buf.getvalue())
            if result:
                return result

            return None
        except Exception as e:
            logger.error(f"OCR error: {e}")
            return None

    @staticmethod
    async def _ocr_space_api(image_data: bytes, ocr_engine: int = 2) -> Optional[str]:
        try:
            url = "https://api.ocr.space/parse/image"
            payload = {"apikey": "helloworld", "language": "eng", "OCREngine": str(ocr_engine), "scale": "true", "isTable": "false", "detectOrientation": "true"}
            async with aiohttp.ClientSession() as session:
                async with session.post(url, data=payload, files={"image": ("captcha.png", image_data, "image/png")}, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                    if resp.status != 200:
                        return None
                    result = await resp.json()
                    if result.get("OCRExitCode") != 1:
                        return None
                    parsed = result.get("ParsedResults", [])
                    if not parsed:
                        return None
                    text = parsed[0].get("ParsedText", "").strip()
                    text = re.sub(r'[\s\n\r]+', '', text)
                    text = re.sub(r'[^a-zA-Z0-9]', '', text)
                    if text and len(text) >= 3:
                        return text
            return None
        except Exception as e:
            logger.warning(f"OCR.space error: {e}")
            return None

    @staticmethod
    async def solve_via_audio(page) -> Optional[str]:
        try:
            audio_btn = await page.query_selector('#captchaControlChallengeCode-switchCaptchaBtn')
            if not audio_btn:
                logger.warning("Audio switch button not found")
                return None
            await audio_btn.click()
            await asyncio.sleep(3)

            audio_src = await page.evaluate("""
                () => {
                    const audio = document.querySelector('audio');
                    if (audio && audio.src) return audio.src;
                    const source = document.querySelector('audio source');
                    if (source && source.src) return source.src;
                    const links = Array.from(document.querySelectorAll('a'));
                    const wav = links.find(a => a.href && (a.href.includes('.wav') || a.href.includes('.mp3')));
                    if (wav) return wav.href;
                    return null;
                }
            """)
            if not audio_src:
                logger.warning("No audio source after switch")
                return None

            async with aiohttp.ClientSession() as session:
                async with session.get(audio_src, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                    if resp.status != 200:
                        return None
                    audio_data = await resp.read()

            with open(f'/opt/render/reports/captcha_audio_{int(time.time())}.wav', 'wb') as f:
                f.write(audio_data)

            # Try Google Speech API
            from core.captcha_solver_open import AudioCaptchaSolver
            text = await AudioCaptchaSolver.solve_audio_captcha(page, audio_url=audio_src)
            if text:
                return text
            return None
        except Exception as e:
            logger.error(f"Audio captcha error: {e}")
            return None

    @staticmethod
    async def solve_captcha(page) -> Optional[str]:
        logger.info("Attempting captcha solve via OCR.space...")
        result = await B2CCaptchaSolver.solve_via_ocr_space(page)
        if result:
            return result

        logger.info("Attempting captcha solve via Audio...")
        result = await B2CCaptchaSolver.solve_via_audio(page)
        if result:
            return result

        logger.info("Refreshing captcha and retrying...")
        try:
            refresh_btn = await page.query_selector('#captchaControlChallengeCode-generateCaptchaBtn')
            if refresh_btn:
                await refresh_btn.click()
                await asyncio.sleep(2)
                result = await B2CCaptchaSolver.solve_via_ocr_space(page)
                if result:
                    return result
        except Exception:
            pass

        return None


# ============================================================
# Stealth Config
# ============================================================

STEALTH_SCRIPTS = [
    """Object.defineProperty(navigator, 'webdriver', { get: () => undefined });""",
    """Object.defineProperty(navigator, 'plugins', { get: () => [1,2,3,4,5] });""",
    """Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });""",
    """Object.defineProperty(navigator, 'hardwareConcurrency', { get: () => 8 });""",
    """Object.defineProperty(navigator, 'deviceMemory', { get: () => 8 });""",
    """
    const getParameter = WebGLRenderingContext.prototype.getParameter;
    WebGLRenderingContext.prototype.getParameter = function(p) {
        if (p === 37445) return 'Intel Inc.';
        if (p === 37446) return 'Intel Iris OpenGL Engine';
        return getParameter.call(this, p);
    };
    """,
]


# ============================================================
# Main Signup Flow
# ============================================================

async def human_type(page, selector: str, text: str, delay_range: tuple = (0.05, 0.15)):
    """Type text with human-like delays."""
    el = await page.query_selector(selector)
    if not el:
        return False
    await el.click()
    await asyncio.sleep(0.3)
    await el.fill("")
    await asyncio.sleep(0.2)
    for char in text:
        await page.keyboard.type(char, delay=random.uniform(delay_range[0], delay_range[1]))
    return True


async def try_signup(identity: Dict, account_num: int, temp_email_info: Optional[Dict] = None) -> Tuple[bool, str, str]:
    from playwright.async_api import async_playwright

    email = identity["email"]
    password = identity["password"]
    first_name = identity["first_name"]
    last_name = identity["last_name"]

    logger.info(f"\n{'='*60}")
    logger.info(f"[Account {account_num}] Attempting signup")
    logger.info(f"  Email:    {email}")
    logger.info(f"  Password: {password}")
    logger.info(f"  Name:     {first_name} {last_name}")
    logger.info(f"{'='*60}")

    pw = await async_playwright().start()
    success = False
    browser = None
    context = None
    page = None

    try:
        browser = await pw.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu", "--window-size=1920,1080"],
        )

        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent=random.choice([
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            ]),
            locale="en-US",
            timezone_id="America/New_York",
            color_scheme="light",
        )

        for script in STEALTH_SCRIPTS:
            await context.add_init_script(script)

        page = await context.new_page()

        # ======================================================================
        # STEP 1: Navigate to genspark.ai
        # ======================================================================
        logger.info(f"[Account {account_num}] Step 1: Navigate to genspark.ai...")
        try:
            await page.goto("https://www.genspark.ai/", wait_until="domcontentloaded", timeout=60000)
        except Exception as e:
            logger.warning(f"Nav issue: {e}")
        await asyncio.sleep(3)

        # Cloudflare check
        title = await page.title()
        if "Just a moment" in title:
            logger.info("Cloudflare challenge detected, waiting...")
            for i in range(30):
                await asyncio.sleep(2)
                try:
                    new_title = await page.title()
                    if "Just a moment" not in new_title:
                        logger.info("Cloudflare passed!")
                        break
                except:
                    pass
                logger.info(f"Waiting for CF... ({i+1}/30)")

        # ======================================================================
        # STEP 2: Click Sign Up button on main page
        # ======================================================================
        logger.info(f"[Account {account_num}] Step 2: Click Sign Up...")

        await page.screenshot(path=f"/opt/render/reports/gs_{account_num}_01_home.png", full_page=True)

        # Look for signup/login buttons
        signup_clicked = False
        selectors = [
            'a[href*="signup"]', 'a[href*="register"]', 'a[href*="sign-up"]',
            'button:has-text("Sign Up")', 'button:has-text("Sign up")',
            'a:has-text("Sign Up")', 'a:has-text("Sign up")',
            'button:has-text("Get Started")', 'a:has-text("Log in")',
            'button:has-text("Log in")', 'a:has-text("Login")',
            '#createAccount', 'button:has-text("Create account")',
        ]

        for sel in selectors:
            try:
                el = await page.query_selector(sel)
                if el and await el.is_visible():
                    logger.info(f"Clicking: {sel}")
                    await el.click()
                    await asyncio.sleep(3)
                    signup_clicked = True
                    break
            except:
                continue

        if not signup_clicked:
            logger.info("No signup button found, trying /signup")
            try:
                await page.goto("https://www.genspark.ai/signup", wait_until="domcontentloaded", timeout=30000)
                await asyncio.sleep(3)
            except:
                pass

        # Wait for B2C redirect
        for i in range(15):
            current_url = page.url
            if "login.genspark" in current_url or "b2c" in current_url or "microsoft" in current_url:
                logger.info(f"B2C detected: {current_url[:80]}...")
                break
            logger.info(f"Waiting for B2C... ({i+1}/15)")
            await asyncio.sleep(2)

        await page.screenshot(path=f"/opt/render/reports/gs_{account_num}_02_b2c.png", full_page=True)

        # ======================================================================
        # STEP 3: Check if we're on signin or signup page
        # ======================================================================
        current_url = page.url

        # Check if there's a signup link on the B2C page (for sign-in page)
        has_signup_link = await page.query_selector('#createAccount')
        if has_signup_link:
            logger.info("Found 'Sign up now' link on B2C, clicking it...")
            await has_signup_link.click()
            await asyncio.sleep(5)

        # Check if we have signup form elements
        has_signup_form = await page.query_selector('#newPassword')
        if not has_signup_form:
            logger.info("No newPassword field yet, checking for signup link...")
            for sel in ['#createAccount', 'a[href*="signup"]', 'a:has-text("Sign up")']:
                try:
                    el = await page.query_selector(sel)
                    if el and await el.is_visible():
                        await el.click()
                        await asyncio.sleep(5)
                        break
                except:
                    continue

        await page.screenshot(path=f"/opt/render/reports/gs_{account_num}_03_form.png", full_page=True)

        # Dump form for debugging
        elements = await page.evaluate("""() => {
            return Array.from(document.querySelectorAll('input, button, select')).map(el => ({
                tag: el.tagName, type: el.type || '', id: el.id || '', name: el.name || '',
                placeholder: el.placeholder || '', text: (el.textContent || '').trim().slice(0, 40),
                visible: el.offsetParent !== null, disabled: el.disabled,
                w: el.getBoundingClientRect().width, h: el.getBoundingClientRect().height,
            })).filter(e => e.visible && e.w > 0 && e.h > 0);
        }""")
        logger.info(f"Form elements: {len(elements)}")
        for el in elements:
            status = "DISABLED" if el['disabled'] else "enabled"
            logger.info(f"  {el['tag']:6s} id={el['id']:40s} type={el['type']:15s} [{status}] text={el['text']} placeholder={el['placeholder']}")

        # ======================================================================
        # STEP 4: Fill email
        # ======================================================================
        logger.info(f"[Account {account_num}] Step 4: Fill email...")
        email_filled = await human_type(page, '#email', email)
        if not email_filled:
            for sel in ['input[type="email"]', 'input[name*="email"]', 'input[placeholder*="email" i]']:
                try:
                    el = await page.query_selector(sel)
                    if el and await el.is_visible():
                        await el.fill(email)
                        email_filled = True
                        break
                except:
                    continue

        await asyncio.sleep(1.5)

        # ======================================================================
        # STEP 5: Handle email verification step (Send verification code)
        # ======================================================================
        send_code_btn = await page.query_selector('#emailVerificationControl_but_send_code')
        if send_code_btn and await send_code_btn.is_visible():
            logger.info(f"[Account {account_num}] Step 5: Email verification required - clicking send code...")
            await send_code_btn.click()
            await asyncio.sleep(2)

            # Create temp email to receive the verification code
            if not temp_email_info:
                logger.info("Creating temp email for verification code...")
                temp_email_info = await TempMailService.create_email()

            if temp_email_info:
                logger.info(f"Temp email: {temp_email_info['email']}")
                # Wait for verification code to arrive
                email_msg = await TempMailService.check_inbox(temp_email_info['token'], timeout=60, poll_interval=5)
                if email_msg:
                    code = TempMailService.extract_code_or_link(email_msg)
                    logger.info(f"Extracted from email: {code}")

                    if code and code.isdigit():
                        # Enter the verification code
                        code_input = await page.query_selector('#emailVerificationControl_but_send_code')
                        # The code input appears after clicking send - looking for the verification code input
                        for sel in ['input[id*="verification"]', 'input[id*="code"]', 'input[name*="code"]',
                                     'input[placeholder*="code" i]', 'input[placeholder*="verify" i]',
                                     '#emailVerificationControl_input_code']:
                            try:
                                inp = await page.query_selector(sel)
                                if inp and await inp.is_visible():
                                    await inp.fill(code)
                                    logger.info(f"Filled verification code: {code}")
                                    await asyncio.sleep(1)
                                    # Click verify button
                                    for verify_sel in ['button:has-text("Verify")', 'button[id*="verify"]',
                                                        'button:has-text("verify")', '#emailVerificationControl_but_verify']:
                                        try:
                                            vbtn = await page.query_selector(verify_sel)
                                            if vbtn and await vbtn.is_visible():
                                                await vbtn.click()
                                                logger.info("Clicked verify button")
                                                await asyncio.sleep(3)
                                                break
                                        except:
                                            continue
                                    break
                            except:
                                continue
                else:
                    logger.warning("No email received for verification code")
            else:
                logger.warning("Could not create temp email")
        else:
            logger.info("No email verification step detected (or already handled)")

        await asyncio.sleep(2)

        # ======================================================================
        # STEP 6: Fill password fields
        # ======================================================================
        logger.info(f"[Account {account_num}] Step 6: Fill passwords...")

        # Check if password field is now enabled
        pw_field = await page.query_selector('#newPassword')
        if pw_field:
            disabled = await pw_field.get_attribute('disabled')
            if disabled:
                logger.warning("Password field still disabled, waiting...")
                for i in range(15):
                    await asyncio.sleep(2)
                    pw_field = await page.query_selector('#newPassword')
                    if pw_field:
                        disabled = await pw_field.get_attribute('disabled')
                        if not disabled:
                            logger.info("Password field now enabled!")
                            break
                    logger.info(f"Waiting for password field to enable... ({i+1}/15)")

        if pw_field:
            await human_type(page, '#newPassword', password)
            await asyncio.sleep(0.5)
            re_pw = await page.query_selector('#reenterPassword')
            if re_pw:
                await human_type(page, '#reenterPassword', password)
                logger.info("Passwords filled")
        else:
            logger.warning("newPassword field not found!")
            for sel in ['input[type="password"]', 'input[name*="password"]']:
                try:
                    el = await page.query_selector(sel)
                    if el and await el.is_visible():
                        await el.fill(password)
                        logger.info(f"Filled password via: {sel}")
                        break
                except:
                    continue

        await asyncio.sleep(2)

        # ======================================================================
        # STEP 7: Solve captcha
        # ======================================================================
        logger.info(f"[Account {account_num}] Step 7: Solve captcha...")

        captcha_text = await B2CCaptchaSolver.solve_captcha(page)

        if captcha_text:
            logger.info(f"Captcha solved: '{captcha_text}'")
            captcha_input = await page.query_selector('#captchaControlChallengeCode')
            if captcha_input:
                await captcha_input.click()
                await asyncio.sleep(0.3)
                await captcha_input.fill(captcha_text)
                logger.info("Filled captcha")
            else:
                for sel in ['input[name*="captcha"]', 'input[id*="captcha"]', 'input[placeholder*="captcha" i]']:
                    try:
                        el = await page.query_selector(sel)
                        if el and await el.is_visible():
                            await el.fill(captcha_text)
                            break
                    except:
                        continue
        else:
            logger.warning("Could not solve captcha!")

        await asyncio.sleep(1)

        # ======================================================================
        # STEP 8: Click Create/Continue
        # ======================================================================
        logger.info(f"[Account {account_num}] Step 8: Click submit...")

        submit_btn = await page.query_selector('#continue')
        if submit_btn:
            await submit_btn.click()
            logger.info("Clicked #continue")
        else:
            for sel in ['button[type="submit"]', 'input[type="submit"]',
                         'button:has-text("Create")', 'button:has-text("Sign up")',
                         'button:has-text("Continue")', 'button:has-text("Register")']:
                try:
                    el = await page.query_selector(sel)
                    if el and await el.is_visible():
                        await el.click()
                        logger.info(f"Clicked: {sel}")
                        break
                except:
                    continue

        await asyncio.sleep(5)

        # ======================================================================
        # STEP 9: Handle post-submit
        # ======================================================================
        await page.screenshot(path=f"/opt/render/reports/gs_{account_num}_09_post.png", full_page=True)

        current_url = page.url
        content = await page.content()
        content_lower = content.lower()

        # Check for errors
        error_texts = []
        for kw in ["error", "invalid", "incorrect", "wrong", "try again", "captcha", "already exists", "already taken"]:
            if kw in content_lower:
                error_texts.append(kw)

        if error_texts:
            logger.warning(f"Errors: {error_texts}")
            if "captcha" in str(error_texts) or "incorrect" in str(error_texts) or "wrong" in str(error_texts) or "try again" in str(error_texts):
                logger.info("Captcha error, trying alternative method...")
                captcha_input = await page.query_selector('#captchaControlChallengeCode')
                if captcha_input:
                    await captcha_input.click()
                    await page.evaluate("document.getElementById('captchaControlChallengeCode').value = ''")
                    await asyncio.sleep(0.5)
                    # Try audio this time
                    captcha_text2 = await B2CCaptchaSolver.solve_via_audio(page)
                    if captcha_text2:
                        await captcha_input.fill(captcha_text2)
                        await asyncio.sleep(1)
                        btn = await page.query_selector('#continue')
                        if btn:
                            await btn.click()
                            await asyncio.sleep(5)

        # ======================================================================
        # STEP 10: Analyze result
        # ======================================================================
        await page.screenshot(path=f"/opt/render/reports/gs_{account_num}_10_final.png", full_page=True)
        final_url = page.url
        final_content = await page.content()
        final_lower = final_content.lower()

        logger.info(f"Final URL: {final_url}")

        # Success indicators
        success_keywords = ["welcome", "dashboard", "home", "profile", "account", "joined", "signed up", "genspark.ai"]
        blocked_keywords = ["error", "invalid", "blocked", "denied", "captcha", "already exists", "try again", "already taken"]

        success_score = sum(1 for kw in success_keywords if kw in final_lower)
        blocked_score = sum(1 for kw in blocked_keywords if kw in final_lower)

        if "login.genspark" not in final_url and "b2c" not in final_url and "microsoft" not in final_url:
            if "genspark" in final_url or "api/auth" in final_url:
                success_score += 5

        logger.info(f"Success: {success_score}, Blocked: {blocked_score}")

        if success_score >= 2 or (success_score > 0 and blocked_score == 0):
            success = True
            logger.info(f">>> SIGNUP SUCCESSFUL: {email} <<<")
        elif success_score > blocked_score:
            success = True
            logger.info(f">>> Signup likely successful (s:{success_score} b:{blocked_score}) <<<")
        else:
            logger.warning(f"Signup ambiguous (s:{success_score} b:{blocked_score})")

        if success:
            print(f"\n!!! ACCOUNT {account_num} CREATED !!!")
            print(f"Email:    {email}")
            print(f"Password: {password}")

    except Exception as e:
        logger.error(f"[Account {account_num}] Error: {e}", exc_info=True)

    finally:
        try:
            if context:
                await context.close()
            if browser:
                await browser.close()
            await pw.stop()
        except:
            pass

    return success, email, password


async def main():
    identity_gen = IdentityGenerator()
    num_accounts = 2
    accounts = []

    for i in range(num_accounts):
        identity = identity_gen.generate_identity()

        # Create temp email for verification code receipt if needed
        temp_email = await TempMailService.create_email()
        if temp_email:
            logger.info(f"Temp email ready: {temp_email['email']}")

        success, email, password = await try_signup(identity, i + 1, temp_email)

        if success:
            accounts.append({"email": email, "password": password})
        else:
            logger.warning(f"Account {i+1} failed")

        if i < num_accounts - 1:
            delay = random.uniform(15, 30)
            logger.info(f"Waiting {delay:.1f}s before next account...")
            await asyncio.sleep(delay)

    print(f"\n{'='*60}")
    print(f"RESULTS: {len(accounts)}/{num_accounts} accounts created")
    print(f"{'='*60}")
    for idx, acc in enumerate(accounts):
        print(f"\nAccount {idx+1}:")
        print(f"  Email:    {acc['email']}")
        print(f"  Password: {acc['password']}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    asyncio.run(main())
