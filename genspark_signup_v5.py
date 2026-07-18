#!/usr/bin/env python3
"""
Genspark.ai Signup Bot v5
Flow: genspark.ai/genspark-claw -> Try Free -> More options -> Sign up now -> B2C form
Uses audio CAPTCHA solving (free, no API key) + mail.tm for temp emails.
Fully async (playwright.async_api).
"""
import asyncio
import base64
import logging
import os
import random
import re
import string
import sys
import time
from io import BytesIO
from typing import Dict, Optional, Tuple

import aiohttp
import requests
from PIL import Image, ImageEnhance, ImageFilter

sys.path.insert(0, "/opt/render/signup-shield-web/backend")
from core.captcha_solver_open import AudioCaptchaSolver

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("genspark-signup-v5")

SCREENSHOT_DIR = "/opt/render/reports"
OCR_API_KEY = "helloworld"
MAILTM_API = "https://api.mail.tm"

FIRST_NAMES = [
    "Aarav", "Vivaan", "Aditya", "Vihaan", "Arjun", "Rohan", "Krishna",
    "Ishaan", "Rahul", "Amit", "Nikhil", "Siddharth", "Dev", "Kabir",
    "Aryan", "Farhan", "Imran", "Zayed", "Rehan", "Vijay", "Deepak",
    "Suresh", "Gaurav", "Ankit", "Praveen", "Sandeep", "Ravi", "Ganesh",
    "Diya", "Saanvi", "Ananya", "Navya", "Myra", "Pari", "Kavya", "Sara",
    "Neha", "Priya", "Sneha", "Pooja", "Riya", "Tanya", "Anika", "Zara",
    "Ishita", "Meera", "Nisha", "Simran", "Divya", "Shreya",
]

LAST_NAMES = [
    "Sharma", "Kumar", "Singh", "Patel", "Gupta", "Reddy", "Nair",
    "Iyer", "Joshi", "Mehta", "Desai", "Shah", "Verma", "Rao",
    "Malhotra", "Chopra", "Banerjee", "Das", "Mishra", "Agarwal",
    "Yadav", "Thakur", "Pandey", "Tiwari", "Bhat", "Menon",
]


class IdentityGenerator:
    def __init__(self):
        self._used_names = set()

    def generate_identity(self) -> Dict:
        first = random.choice(FIRST_NAMES)
        last = random.choice(LAST_NAMES)
        full_name = f"{first} {last}"
        while full_name in self._used_names:
            first = random.choice(FIRST_NAMES)
            last = random.choice(LAST_NAMES)
            full_name = f"{first} {last}"
        self._used_names.add(full_name)
        return {"first": first, "last": last, "full_name": full_name}


class MailTMClient:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json",
            "Content-Type": "application/json",
        })
        self.base_url = MAILTM_API
        self.token = None
        self.account_id = None
        self.email_address = None

    def create_account(self) -> str:
        resp = self.session.get(f"{self.base_url}/domains")
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, list):
            domains = data
        else:
            domains = data.get("hydra:member", [])
        domain = domains[0]["domain"] if domains else "web-library.net"

        ts = int(time.time() * 1000000) % 100000000
        rnd = random.randint(100000, 999999)
        local_part = f"u{ts}_{rnd}"
        email = f"{local_part}@{domain}"
        password = f"Pass{ts}!"

        resp = self.session.post(
            f"{self.base_url}/accounts",
            json={"address": email, "password": password}
        )
        if resp.status_code == 201:
            data = resp.json()
            self.account_id = data.get("id")
            self.email_address = data.get("address")
            resp = self.session.post(
                f"{self.base_url}/token",
                json={"address": email, "password": password}
            )
            if resp.status_code == 200:
                self.token = resp.json().get("token")
                self.session.headers.update({
                    "Authorization": f"Bearer {self.token}"
                })
                logger.info(f"mail.tm account: {self.email_address}")
                return self.email_address
        elif resp.status_code == 429:
            time.sleep(10)
            return self.create_account()
        raise Exception(f"mail.tm error: {resp.status_code}")

    def wait_for_code(self, timeout: int = 180) -> str:
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                resp = self.session.get(f"{self.base_url}/messages", params={"page": 1})
                if resp.status_code == 200:
                    data = resp.json()
                    messages = data if isinstance(data, list) else data.get("hydra:member", [])
                    for msg in messages:
                        msg_id = msg.get("id")
                        mr = self.session.get(f"{self.base_url}/messages/{msg_id}")
                        if mr.status_code == 200:
                            j = mr.json()
                            body = j.get("text", "")
                            html = j.get("html", [])
                            combined = body
                            for b in (html or []):
                                if isinstance(b, dict):
                                    combined += " " + b.get("value", "")
                            codes = re.findall(r'(\d{4,8})', combined)
                            if codes:
                                logger.info(f"Code: {codes[0]}")
                                return codes[0]
            except Exception as e:
                logger.warning(f"Mail check error: {e}")
            time.sleep(5)
        raise TimeoutError(f"No code within {timeout}s")

    def cleanup(self):
        if self.account_id and self.token:
            try:
                self.session.delete(f"{self.base_url}/accounts/{self.account_id}")
            except:
                pass


class GensparkSignupBot:
    def __init__(self, identity: Dict, mail_client: MailTMClient):
        self.identity = identity
        self.mail = mail_client
        self.email = mail_client.email_address
        self.password = self._generate_password()
        self.browser = None
        self.page = None
        self.context = None

    def _generate_password(self) -> str:
        chars = string.ascii_letters + string.digits
        return ''.join(random.choice(chars) for _ in range(14))

    async def _random_delay(self, min_s=0.5, max_s=2.0):
        await asyncio.sleep(random.uniform(min_s, max_s))

    async def _take_screenshot(self, name: str):
        if self.page:
            ts = int(time.time())
            path = os.path.join(SCREENSHOT_DIR, f"{name}_{ts}.png")
            try:
                await self.page.screenshot(path=path, full_page=True)
            except:
                pass

    async def _apply_stealth(self, page):
        scripts = [
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});",
            """window.chrome = {runtime: {connect: () => ({}), sendMessage: () => {}, onMessage: {addListener: () => {}}}, loadTimes: () => {}};""",
            "Object.defineProperty(navigator, 'plugins', {get: () => [1,2,3]});",
            "Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});",
        ]
        for script in scripts:
            try:
                await page.add_init_script(script)
            except:
                pass
        logger.info("Stealth scripts applied")

    async def _solve_captcha_ocr(self) -> Optional[str]:
        """Try OCR.space on the captcha image (data URI for quality)."""
        img_bytes = None
        try:
            data_uri = await self.page.evaluate("""
                () => {
                    const img = document.getElementById('captchaControlChallengeCode-img');
                    return img ? img.src : null;
                }
            """)
            if data_uri and data_uri.startswith('data:image'):
                header, encoded = data_uri.split(',', 1)
                img_bytes = base64.b64decode(encoded)
        except Exception as e:
            logger.warning(f"Data URI error: {e}")

        if not img_bytes:
            try:
                for sel in ["#captchaControlChallengeCode-img", "#captchaImage", "[class*='captcha'] img"]:
                    el = self.page.locator(sel).first
                    if await el.is_visible(timeout=1000):
                        img_bytes = await el.screenshot()
                        break
            except:
                pass

        if not img_bytes:
            return None

        # Enhance for OCR
        try:
            img = Image.open(BytesIO(img_bytes))
            gray = img.convert('L')
            enhanced = ImageEnhance.Contrast(gray).enhance(3.0)
            enhanced = enhanced.filter(ImageFilter.SHARPEN)
            bw = enhanced.point(lambda x, t=160: 255 if x > t else 0)

            ts = int(time.time())
            bw.save(os.path.join(SCREENSHOT_DIR, f"captcha_enhanced_{ts}.png"))

            buf = BytesIO()
            bw.save(buf, format='PNG')
            enhanced_bytes = buf.getvalue()

            for engine in [2, 1]:
                try:
                    resp = requests.post(
                        "https://api.ocr.space/parse/image",
                        files={"file": ("captcha.png", BytesIO(enhanced_bytes), "image/png")},
                        data={
                            "apikey": OCR_API_KEY,
                            "language": "eng",
                            "OCREngine": engine,
                            "isOverlayRequired": False,
                            "scale": "true",
                        },
                        timeout=30,
                    )
                    if resp.status_code == 200:
                        result = resp.json()
                        if not result.get("IsErroredOnProcessing"):
                            text = result.get("ParsedResults", [{}])[0].get("ParsedText", "").strip()
                            text = re.sub(r'[\s\n\r]+', '', text)
                            if text and len(text) >= 3:
                                logger.info(f"OCR result: '{text}'")
                                return text
                except:
                    pass
        except Exception as e:
            logger.warning(f"OCR processing error: {e}")
        return None

    async def _solve_captcha_audio(self) -> Optional[str]:
        """Switch to audio captcha and transcribe via Google Speech."""
        try:
            for sel in ["#captchaControlChallengeCode-switchCaptchaBtn",
                         "a:has-text('Switch')", "[id*='switchCaptcha']"]:
                btn = self.page.locator(sel).first
                if await btn.is_visible(timeout=1000):
                    await btn.click()
                    logger.info(f"Clicked audio switch: {sel}")
                    await asyncio.sleep(3)
                    break
            else:
                logger.warning("Audio switch not found")
                return None

            audio_url = await self.page.evaluate("""
                () => {
                    const a = document.querySelector('audio');
                    if (a && a.src) return a.src;
                    const s = document.querySelector('audio source');
                    if (s && s.src) return s.src;
                    return null;
                }
            """)
            if not audio_url:
                logger.warning("No audio URL found")
                return None

            logger.info(f"Audio URL: {audio_url[:80]}...")
            text = await AudioCaptchaSolver.solve_audio_captcha(
                page=None, audio_url=audio_url
            )
            if text:
                logger.info(f"Audio transcribed: '{text}'")
                return text
        except Exception as e:
            logger.warning(f"Audio captcha error: {e}")
        return None

    async def _solve_captcha(self) -> Optional[str]:
        """Try OCR first, then audio, then refresh + retry."""
        result = await self._solve_captcha_ocr()
        if result:
            return result
        result = await self._solve_captcha_audio()
        if result:
            return result
        # Refresh and retry once
        try:
            btn = self.page.locator("#captchaControlChallengeCode-generateCaptchaBtn").first
            if await btn.is_visible(timeout=2000):
                await btn.click()
                await asyncio.sleep(3)
                result = await self._solve_captcha_ocr()
                if result:
                    return result
        except:
            pass
        return None

    async def run(self, headless: bool = True) -> Tuple[bool, str]:
        from playwright.async_api import async_playwright

        result = False
        msg = ""

        try:
            async with async_playwright() as p:
                logger.info("Launching browser...")
                self.browser = await p.chromium.launch(
                    headless=headless,
                    args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"],
                )
                self.context = await self.browser.new_context(
                    viewport={"width": 1366, "height": 768},
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                    locale="en-US",
                )
                await self._apply_stealth(self.context)

                self.page = await self.context.new_page()

                # === Step 1: Navigate ===
                logger.info("Step 1: Navigate to genspark.ai/genspark-claw...")
                try:
                    await self.page.goto("https://www.genspark.ai/genspark-claw", wait_until="domcontentloaded", timeout=30000)
                except Exception as e:
                    logger.warning(f"Nav timeout: {e}")
                try:
                    await self.page.wait_for_load_state("networkidle", timeout=20000)
                except:
                    pass
                await self._random_delay(3, 5)
                await self._take_screenshot("01_claw_page")

                # === Step 2: "Try Free" ===
                logger.info("Step 2: Try Free...")
                clicked = False
                for btn_sel in [
                    'button:has-text("Try Free")',
                ]:
                    try:
                        btn = self.page.locator(btn_sel).first
                        if await btn.is_visible(timeout=5000):
                            await btn.click()
                            logger.info(f"Clicked Try Free")
                            clicked = True
                            break
                    except:
                        continue
                if not clicked:
                    logger.warning("Try Free not found")
                await self._random_delay(4, 6)
                await self._take_screenshot("02_after_try_free")

                # === Step 3: "More options" ===
                logger.info("Step 3: More options...")
                for sel in ['button:has-text("More options")']:
                    try:
                        btn = self.page.locator(sel).first
                        if await btn.is_visible(timeout=5000):
                            await btn.click()
                            logger.info("Clicked More options")
                            break
                    except:
                        continue
                await self._random_delay(3, 5)
                await self._take_screenshot("03_after_more_options")

                # === Step 4: "Sign up now" ===
                logger.info("Step 4: Sign up now...")
                for sel in ["#createAccount", 'a:has-text("Sign up")']:
                    try:
                        link = self.page.locator(sel).first
                        if await link.is_visible(timeout=5000):
                            await link.click()
                            logger.info(f"Clicked signup: {sel}")
                            break
                    except:
                        continue
                await self._random_delay(4, 6)
                await self._take_screenshot("04_signup_form")

                # === Step 5: Fill email ===
                logger.info("Step 5: Fill email...")
                email_input = None
                target_frame = self.page
                for frame in self.page.frames:
                    try:
                        el = frame.locator("#email").first
                        if await el.is_visible(timeout=2000):
                            email_input = el
                            target_frame = frame
                            logger.info(f"Email field in frame: {frame.name}")
                            break
                    except:
                        continue

                if not email_input:
                    await self._take_screenshot("05_no_email")
                    raise Exception("Email field not found")

                await email_input.fill(self.email)
                logger.info(f"Email: {self.email}")
                await self._random_delay(1, 2)

                # === Step 6: Solve captcha ===
                logger.info("Step 6: Solve captcha...")
                await self._take_screenshot("06_before_captcha")
                captcha_text = await self._solve_captcha()
                if captcha_text:
                    for sel in ["#captchaControlChallengeCode", 'input[name*="captcha"]', 'input[id*="captcha"]']:
                        try:
                            inp = target_frame.locator(sel).first
                            if await inp.is_visible(timeout=1000):
                                await inp.fill(captcha_text)
                                logger.info(f"Captcha filled: {captcha_text}")
                                break
                        except:
                            continue
                else:
                    logger.warning("Captcha not solved, continuing...")
                await self._random_delay(1, 2)

                # === Step 7: Send verification code ===
                logger.info("Step 7: Send verification code...")
                for sel in ["#emailVerificationControl_but_send_code", 'button:has-text("Send")']:
                    try:
                        btn = target_frame.locator(sel).first
                        if await btn.is_visible(timeout=5000):
                            await btn.click()
                            logger.info(f"Clicked send: {sel}")
                            break
                    except:
                        continue
                await self._random_delay(3, 5)
                await self._take_screenshot("07_after_send")

                # === Step 8: Wait for code ===
                logger.info("Step 8: Wait for code...")
                code = None
                try:
                    code = self.mail.wait_for_code(timeout=180)
                    logger.info(f"Got code: {code}")
                except TimeoutError:
                    await self._take_screenshot("08_timeout")
                    logger.warning("Timeout, trying resend...")
                    for sel in ["#emailVerificationControl_but_resend", 'button:has-text("Resend")']:
                        try:
                            btn = target_frame.locator(sel).first
                            if await btn.is_visible(timeout=3000):
                                await btn.click()
                                logger.info("Resend clicked")
                                await self._random_delay(2, 3)
                                code = self.mail.wait_for_code(timeout=120)
                                if code:
                                    logger.info(f"Got code on retry: {code}")
                                break
                        except:
                            continue

                if not code:
                    raise Exception("No verification code")

                # === Step 9: Enter code ===
                logger.info("Step 9: Enter code...")
                for sel in ["#emailVerificationControl_input_code", "input[id*='code']"]:
                    try:
                        inp = target_frame.locator(sel).first
                        if await inp.is_visible(timeout=2000):
                            await inp.fill(code)
                            logger.info("Code entered")
                            break
                    except:
                        continue
                else:
                    await target_frame.keyboard.type(code)

                await self._random_delay(1, 2)
                for sel in ["#emailVerificationControl_but_verify", 'button:has-text("Verify")']:
                    try:
                        vbtn = target_frame.locator(sel).first
                        if await vbtn.is_visible(timeout=2000):
                            await vbtn.click()
                            logger.info("Verify clicked")
                            break
                    except:
                        continue
                await self._random_delay(2, 3)
                await self._take_screenshot("09_after_verify")

                # === Step 10: Fill password ===
                logger.info("Step 10: Fill password...")
                try:
                    await self.page.wait_for_function(
                        "() => { const p = document.querySelector('#newPassword'); return p && !p.disabled; }",
                        timeout=20000
                    )
                except:
                    pass

                for sel_pwd in ["#newPassword"]:
                    try:
                        pwd = target_frame.locator(sel_pwd).first
                        if await pwd.is_visible(timeout=2000):
                            await pwd.fill(self.password)
                            await asyncio.sleep(0.5)
                            confirm = target_frame.locator("#reenterPassword").first
                            await confirm.fill(self.password)
                            logger.info("Password filled")
                            break
                    except:
                        continue
                await self._random_delay(1, 2)
                await self._take_screenshot("10_after_password")

                # === Step 11: Create ===
                logger.info("Step 11: Create account...")
                for sel in ["#continue", "input[value='Create']", 'button:has-text("Create")']:
                    try:
                        btn = target_frame.locator(sel).first
                        if await btn.is_visible(timeout=5000):
                            await btn.click()
                            logger.info(f"Clicked: {sel}")
                            break
                    except:
                        continue
                await self._random_delay(5, 8)
                await self._take_screenshot("11_result")

                # === Step 12: Check ===
                logger.info("Step 12: Check result...")
                current_url = self.page.url
                logger.info(f"URL: {current_url}")

                for err_sel in [".error", "[class*='error']", "#identityError"]:
                    try:
                        err = target_frame.locator(err_sel).first
                        if await err.is_visible(timeout=1000):
                            err_text = await err.text_content()
                            if err_text.strip():
                                logger.warning(f"Error: {err_text.strip()}")
                                return False, f"Error: {err_text.strip()}"
                    except:
                        continue

                result = True
                msg = f"Email: {self.email}\nPassword: {self.password}"
                return result, msg

        except Exception as e:
            logger.error(f"Signup failed: {e}")
            import traceback
            traceback.print_exc()
            return False, str(e)
        finally:
            if self.browser:
                try:
                    await self.browser.close()
                except:
                    pass


async def create_single_account() -> Tuple[bool, str, Optional[MailTMClient]]:
    identity_gen = IdentityGenerator()
    identity = identity_gen.generate_identity()
    logger.info(f"Identity: {identity['full_name']}")

    mail = MailTMClient()
    try:
        mail.create_account()
        logger.info(f"Temp email: {mail.email_address}")
        bot = GensparkSignupBot(identity, mail)
        success, msg = await bot.run(headless=True)
        if success:
            return True, msg, mail
        else:
            mail.cleanup()
            return False, msg, None
    except Exception as e:
        logger.error(f"Error: {e}")
        mail.cleanup()
        return False, str(e), None


async def main():
    num_accounts = 2
    accounts = []

    for i in range(num_accounts):
        logger.info(f"\n{'='*60}")
        logger.info(f"Account {i+1}/{num_accounts}")
        logger.info(f"{'='*60}")

        success, msg, mail = await create_single_account()
        if success:
            accounts.append(msg)
            logger.info(f"SUCCESS: {msg}")
        else:
            logger.error(f"FAILED: {msg}")
            await asyncio.sleep(5)
            success2, msg2, mail2 = await create_single_account()
            if success2:
                accounts.append(msg2)
                logger.info(f"SUCCESS on retry: {msg2}")
            else:
                logger.error(f"Retry failed: {msg2}")

        if i < num_accounts - 1:
            delay = random.uniform(5, 10)
            logger.info(f"Wait {delay:.0f}s...")
            await asyncio.sleep(delay)

    print("\n\n=== ACCOUNT CREDENTIALS ===")
    for acc in accounts:
        print(acc)
        print("---")
    print("=== END ===")


if __name__ == "__main__":
    asyncio.run(main())
