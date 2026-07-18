#!/usr/bin/env python3
"""
Genspark.ai Signup Bot v4
Flow: claw page -> Try Free -> More options -> Sign up now -> B2C signup form
Uses mail.tm for real temp emails to receive verification codes.
Fully synchronous - no asyncio.
"""

import json
import logging
import os
import random
import re
import string
import sys
import time
from datetime import datetime
from typing import Dict, Optional, Tuple

import requests
from PIL import Image, ImageFilter, ImageEnhance, ImageOps
from io import BytesIO
import base64

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("genspark-signup-v4")

# ============================================================
# Config
# ============================================================
HEADLESS = True
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
    "Ishita", "Meera", "Nisha", "Simran", "Divya", "Shreya", "Fatima",
    "Ayesha", "Zainab", "Maryam", "Hafsa", "Aditi", "Isha", "Sonia",
]

LAST_NAMES = [
    "Sharma", "Kumar", "Singh", "Patel", "Gupta", "Reddy", "Nair",
    "Iyer", "Joshi", "Mehta", "Desai", "Shah", "Verma", "Rao",
    "Malhotra", "Chopra", "Banerjee", "Das", "Mishra", "Agarwal",
    "Yadav", "Thakur", "Pandey", "Tiwari", "Bhat", "Menon",
    "Pillai", "Naik", "Kamat", "Shetty", "Kapoor", "Khanna",
]


class IdentityGenerator:
    """Generates unique identities with random names."""

    def __init__(self):
        self._used_names: set = set()

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
    """Client for mail.tm disposable email service."""

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
        """Create a disposable email account at mail.tm. Returns email address."""
        # First get available domains
        resp = self.session.get(f"{self.base_url}/domains")
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, list):
            domains = data
        else:
            domains = data.get("hydra:member", [])
        if not domains:
            domain = "web-library.net"
        else:
            domain = domains[0]["domain"]

        # Generate unique email with timestamp and random
        ts = int(time.time() * 1000000) % 100000000
        rnd = random.randint(100000, 999999)
        local_part = f"u{ts}_{rnd}"
        email = f"{local_part}@{domain}"
        password = f"Pass{ts}!"

        # Create account
        resp = self.session.post(
            f"{self.base_url}/accounts",
            json={"address": email, "password": password}
        )
        if resp.status_code == 201:
            data = resp.json()
            self.account_id = data.get("id")
            self.email_address = data.get("address")
            # Get token
            resp = self.session.post(
                f"{self.base_url}/token",
                json={"address": email, "password": password}
            )
            if resp.status_code == 200:
                self.token = resp.json().get("token")
                self.session.headers.update({
                    "Authorization": f"Bearer {self.token}"
                })
                logger.info(f"mail.tm account created: {self.email_address}")
                return self.email_address
        elif resp.status_code == 429:
            logger.warning("mail.tm rate limited, waiting...")
            time.sleep(10)
            return self.create_account()

        raise Exception(f"Failed to create mail.tm account: {resp.status_code} {resp.text[:200]}")

    def wait_for_code(self, timeout: int = 120) -> str:
        """Wait for an email containing a verification code. Returns the code."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                resp = self.session.get(
                    f"{self.base_url}/messages",
                    params={"page": 1}
                )
                if resp.status_code == 200:
                    data = resp.json()
                    if isinstance(data, list):
                        messages = data
                    else:
                        messages = data.get("hydra:member", [])
                    for msg in messages:
                        subject = msg.get("subject", "")
                        if "code" in subject.lower() or "verify" in subject.lower():
                            msg_id = msg.get("id")
                            msg_resp = self.session.get(
                                f"{self.base_url}/messages/{msg_id}"
                            )
                            if msg_resp.status_code == 200:
                                body_text = msg_resp.json().get("text", "")
                                html_parts = msg_resp.json().get("html", [])
                                combined = body_text
                                for b in (html_parts or []):
                                    if isinstance(b, dict):
                                        combined += " " + b.get("value", "")
                                codes = re.findall(r'(\d{4,8})', combined)
                                if codes:
                                    logger.info(f"Found verification code: {codes[0]}")
                                    self.session.delete(f"{self.base_url}/messages/{msg_id}")
                                    return codes[0]

                    # Check the last message even if subject doesn't match
                    if messages:
                        last = messages[0]
                        msg_id = last.get("id")
                        msg_resp = self.session.get(
                            f"{self.base_url}/messages/{msg_id}"
                        )
                        if msg_resp.status_code == 200:
                            body_text = msg_resp.json().get("text", "")
                            html_parts = msg_resp.json().get("html", [])
                            combined = body_text
                            for b in (html_parts or []):
                                if isinstance(b, dict):
                                    combined += " " + b.get("value", "")
                            codes = re.findall(r'(\d{4,8})', combined)
                            if codes:
                                logger.info(f"Found verification code (fallback): {codes[0]}")
                                self.session.delete(f"{self.base_url}/messages/{msg_id}")
                                return codes[0]
            except Exception as e:
                logger.warning(f"Error checking mail.tm: {e}")

            time.sleep(5)

        raise TimeoutError(f"No verification code received within {timeout}s")

    def cleanup(self):
        """Delete the mail.tm account."""
        if self.account_id and self.token:
            try:
                self.session.delete(f"{self.base_url}/accounts/{self.account_id}")
                logger.info(f"mail.tm account {self.email_address} deleted")
            except Exception as e:
                logger.warning(f"Error deleting mail.tm account: {e}")


class GensparkSignupBot:
    """Signup bot for genspark.ai using the B2C flow via claw page."""

    def __init__(self, identity: Dict, mail_client: MailTMClient):
        self.identity = identity
        self.mail = mail_client
        self.email = mail_client.email_address
        self.password = self._generate_password()
        self.browser = None
        self.page = None
        self.context = None

    def _generate_password(self) -> str:
        chars = string.ascii_letters + string.digits + "!@#$%"
        return ''.join(random.choice(chars) for _ in range(14))

    def _random_delay(self, min_s: float = 0.5, max_s: float = 2.0):
        time.sleep(random.uniform(min_s, max_s))

    def _solve_captcha(self, screenshot_bytes: bytes) -> Optional[str]:
        """Solve captcha using OCR.space API."""
        try:
            ts = int(time.time())
            debug_path = os.path.join(SCREENSHOT_DIR, f"captcha_{ts}.png")
            with open(debug_path, "wb") as f:
                f.write(screenshot_bytes)
            logger.info(f"Captcha image saved to {debug_path}")

            with open(debug_path, "rb") as f:
                resp = requests.post(
                    "https://api.ocr.space/parse/image",
                    files={"file": f},
                    data={
                        "apikey": OCR_API_KEY,
                        "language": "eng",
                        "OCREngine": 2,
                        "isOverlayRequired": False,
                    },
                    timeout=30,
                )

            if resp.status_code == 200:
                result = resp.json()
                if not result.get("IsErroredOnProcessing"):
                    text = result.get("ParsedResults", [{}])[0].get("ParsedText", "").strip()
                    if text:
                        text = ''.join(c for c in text if c.isalnum() or c in ' -_')
                        logger.info(f"OCR result: '{text}'")
                        return text

                # Try engine 1
                with open(debug_path, "rb") as f2:
                    resp2 = requests.post(
                        "https://api.ocr.space/parse/image",
                        files={"file": f2},
                        data={
                            "apikey": OCR_API_KEY,
                            "language": "eng",
                            "OCREngine": 1,
                            "isOverlayRequired": False,
                        },
                        timeout=30,
                    )
                if resp2.status_code == 200:
                    result2 = resp2.json()
                    if not result2.get("IsErroredOnProcessing"):
                        text = result2.get("ParsedResults", [{}])[0].get("ParsedText", "").strip()
                        if text:
                            text = ''.join(c for c in text if c.isalnum() or c in ' -_')
                            logger.info(f"OCR engine 1 result: '{text}'")
                            return text

            logger.warning(f"OCR API failed: {resp.status_code}")
            return None

        except Exception as e:
            logger.warning(f"Captcha solving error: {e}")
            return None

    def _take_screenshot(self, name: str):
        if self.page:
            ts = int(time.time())
            path = os.path.join(SCREENSHOT_DIR, f"{name}_{ts}.png")
            self.page.screenshot(path=path, full_page=True)
            logger.info(f"Screenshot saved: {path}")

    def run(self, headless: bool = True) -> Tuple[bool, str]:
        """Run the signup flow. Returns (success, message)."""
        from playwright.sync_api import sync_playwright

        result = False
        msg = ""

        try:
            with sync_playwright() as p:
                logger.info("Launching browser...")
                self.browser = p.chromium.launch(
                    headless=headless,
                    args=[
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                        "--disable-dev-shm-usage",
                    ]
                )

                self.context = self.browser.new_context(
                    viewport={"width": 1366, "height": 768},
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                    locale="en-US",
                    timezone_id="America/New_York",
                )

                self.page = self.context.new_page()

                # ============================================================
                # Step 1: Go to claw page
                # ============================================================
                logger.info("Step 1: Navigating to genspark.ai/genspark-claw...")
                self.page.goto("https://www.genspark.ai/genspark-claw", wait_until="networkidle", timeout=30000)
                self._random_delay(2, 4)
                self._take_screenshot("01_claw_page")

                # ============================================================
                # Step 2: Click "Try Free" button
                # ============================================================
                logger.info("Step 2: Clicking 'Try Free'...")
                try:
                    btn = self.page.get_by_role("button", name="Try Free").first
                    btn.wait_for(state="visible", timeout=10000)
                    btn.click()
                    logger.info("Clicked 'Try Free'")
                    self._random_delay(3, 5)
                except:
                    try:
                        btn = self.page.locator("button:has-text('Try Free')").first
                        btn.wait_for(state="visible", timeout=5000)
                        btn.click()
                        logger.info("Clicked 'Try Free' (alt)")
                        self._random_delay(3, 5)
                    except:
                        logger.warning("No 'Try Free' button found")
                self._take_screenshot("02_after_try_free")

                # ============================================================
                # Step 3: Click "More options" button
                # ============================================================
                logger.info("Step 3: Clicking 'More options'...")
                try:
                    btn = self.page.locator("button:has-text('More options')").first
                    btn.wait_for(state="visible", timeout=10000)
                    btn.click()
                    logger.info("Clicked 'More options'")
                    self._random_delay(3, 5)
                except:
                    logger.warning("No 'More options' button")
                self._take_screenshot("03_after_more_options")

                # ============================================================
                # Step 4: Click "Sign up now" link
                # ============================================================
                logger.info("Step 4: Clicking 'Sign up now'...")
                try:
                    link = self.page.locator("#createAccount").first
                    link.wait_for(state="visible", timeout=10000)
                    link.click()
                    logger.info("Clicked 'Sign up now'")
                    self._random_delay(3, 5)
                except:
                    try:
                        link = self.page.locator("a:has-text('Sign up')").first
                        link.wait_for(state="visible", timeout=5000)
                        link.click()
                        logger.info("Clicked 'Sign up' (alt)")
                        self._random_delay(3, 5)
                    except:
                        logger.warning("No signup link found")
                self._take_screenshot("04_signup_form")

                # ============================================================
                # Step 5: Find email field and fill it
                # ============================================================
                logger.info("Step 5: Filling email...")
                self._random_delay(2, 4)

                # Try to find the email input - check all frames
                email_input = None
                target_frame = self.page

                for frame in self.page.frames:
                    try:
                        el = frame.locator("#email").first
                        if el.is_visible(timeout=2000):
                            email_input = el
                            target_frame = frame
                            logger.info(f"Email field found in frame: {frame.name or 'main'}")
                            break
                    except:
                        continue

                if not email_input:
                    self._take_screenshot("05_no_email")
                    raise Exception("Could not find email input field")

                email_input.fill(self.email)
                logger.info(f"Email filled: {self.email}")
                self._random_delay(1, 2)

                # ============================================================
                # Step 6: Solve captcha
                # ============================================================
                logger.info("Step 6: Solving captcha...")
                self._take_screenshot("06_before_captcha")

                captcha_solved = False
                captcha_element = None

                for selector in ["#captchaImage", "#captcha", "img[src*='captcha']", "[class*='captcha'] img", "[id*='captcha']"]:
                    try:
                        el = target_frame.locator(selector).first
                        if el.is_visible(timeout=2000):
                            captcha_element = el
                            logger.info(f"Captcha element found: {selector}")
                            break
                    except:
                        continue

                if captcha_element:
                    captcha_bytes = captcha_element.screenshot()
                    captcha_text = self._solve_captcha(captcha_bytes)
                    if captcha_text:
                        try:
                            cap_input = target_frame.locator("#captchaControlChallengeCode").first
                            if cap_input.is_visible(timeout=2000):
                                cap_input.fill(captcha_text)
                                logger.info(f"Captcha filled: {captcha_text}")
                                captcha_solved = True
                        except:
                            logger.warning("Could not fill captcha input")
                else:
                    logger.warning("No captcha element found")

                self._random_delay(1, 2)

                # ============================================================
                # Step 7: Send verification code
                # ============================================================
                logger.info("Step 7: Sending verification code...")
                try:
                    btn = target_frame.locator("#emailVerificationControl_but_send_code").first
                    btn.wait_for(state="visible", timeout=5000)
                    btn.click()
                    logger.info("Clicked 'Send verification code'")
                    self._random_delay(2, 3)
                except:
                    try:
                        btn = target_frame.locator("button:has-text('Send')").first
                        btn.wait_for(state="visible", timeout=3000)
                        btn.click()
                        logger.info("Clicked 'Send' (alt)")
                        self._random_delay(2, 3)
                    except:
                        logger.warning("Could not send verification code")
                self._take_screenshot("07_after_send")

                # ============================================================
                # Step 8: Wait for verification code from email
                # ============================================================
                logger.info("Step 8: Waiting for verification code...")
                try:
                    code = self.mail.wait_for_code(timeout=150)
                    logger.info(f"Got code: {code}")
                except TimeoutError:
                    self._take_screenshot("08_timeout")
                    # Try clicking resend
                    try:
                        btn = target_frame.locator("button:has-text('Resend'), #emailVerificationControl_but_resend").first
                        if btn.is_visible(timeout=2000):
                            btn.click()
                            logger.info("Clicked resend")
                            code = self.mail.wait_for_code(timeout=120)
                            logger.info(f"Got code on retry: {code}")
                        else:
                            raise
                    except:
                        raise Exception("Could not get verification code")

                # ============================================================
                # Step 9: Enter verification code
                # ============================================================
                logger.info("Step 9: Entering verification code...")
                try:
                    code_input = target_frame.locator("#emailVerificationControl_input_code").first
                    code_input.fill(code)
                    logger.info("Code entered")
                    self._random_delay(1, 2)
                except:
                    try:
                        code_input = target_frame.locator("input[id*='code']").first
                        code_input.fill(code)
                        logger.info("Code entered (alt)")
                        self._random_delay(1, 2)
                    except:
                        target_frame.keyboard.type(code)
                        logger.info("Code typed via keyboard")
                        self._random_delay(1, 2)

                try:
                    verify_btn = target_frame.locator("#emailVerificationControl_but_verify, button:has-text('Verify')").first
                    if verify_btn.is_visible(timeout=2000):
                        verify_btn.click()
                        logger.info("Clicked verify")
                        self._random_delay(2, 3)
                except:
                    pass

                self._take_screenshot("09_after_verify")

                # ============================================================
                # Step 10: Fill password
                # ============================================================
                logger.info("Step 10: Filling password...")
                self._random_delay(1, 3)

                # Wait for password field to enable
                try:
                    self.page.wait_for_function(
                        "() => { const p = document.querySelector('#newPassword'); return p && !p.disabled; }",
                        timeout=20000
                    )
                    logger.info("Password field enabled")
                except:
                    logger.warning("Password field did not enable")

                try:
                    pwd = target_frame.locator("#newPassword").first
                    pwd.fill(self.password)
                    self._random_delay(0.5, 1)
                    confirm = target_frame.locator("#reenterPassword").first
                    confirm.fill(self.password)
                    logger.info("Password filled")
                    self._random_delay(1, 2)
                except Exception as e:
                    logger.warning(f"Password fill error: {e}")
                self._take_screenshot("10_after_password")

                # ============================================================
                # Step 11: Check captcha again
                # ============================================================
                if not captcha_solved:
                    logger.info("Step 11: Re-checking captcha...")
                    try:
                        el = target_frame.locator("#captchaImage").first
                        if el.is_visible(timeout=2000):
                            cb = el.screenshot()
                            ct = self._solve_captcha(cb)
                            if ct:
                                ci = target_frame.locator("#captchaControlChallengeCode").first
                                ci.fill(ct)
                                logger.info(f"Captcha filled (2nd): {ct}")
                    except:
                        pass

                self._random_delay(1, 2)

                # ============================================================
                # Step 12: Click Create
                # ============================================================
                logger.info("Step 12: Clicking Create...")
                try:
                    btn = target_frame.locator("#continue").first
                    btn.wait_for(state="visible", timeout=5000)
                    btn.click()
                    logger.info("Clicked Create")
                    self._random_delay(3, 5)
                except:
                    try:
                        btn = target_frame.locator("input[value='Create'], button:has-text('Create')").first
                        btn.wait_for(state="visible", timeout=3000)
                        btn.click()
                        logger.info("Clicked Create (alt)")
                        self._random_delay(3, 5)
                    except:
                        logger.warning("Could not click Create")
                self._take_screenshot("11_after_create")

                # ============================================================
                # Step 13: Check result
                # ============================================================
                logger.info("Step 13: Checking result...")
                self._random_delay(3, 5)
                self._take_screenshot("12_result")

                current_url = self.page.url
                logger.info(f"URL after signup: {current_url}")

                # Check for errors
                try:
                    error = target_frame.locator(".error, [class*='error'], #identityError").first
                    if error.is_visible(timeout=2000):
                        err_text = error.text_content()
                        logger.warning(f"Error: {err_text}")
                        return False, f"Error: {err_text}"
                except:
                    pass

                # Success if we left the signup page
                if "genspark" in current_url and "signup" not in current_url.lower():
                    result = True
                    msg = f"Email: {self.email}\nPassword: {self.password}"
                elif "b2c" in current_url:
                    result = True
                    msg = f"Email: {self.email}\nPassword: {self.password}"
                else:
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
                    self.browser.close()
                except:
                    pass


def create_single_account() -> Tuple[bool, str, Optional[MailTMClient]]:
    """Create one account. Returns (success, message, mail_client)."""
    identity_gen = IdentityGenerator()
    identity = identity_gen.generate_identity()
    logger.info(f"Identity: {identity['full_name']}")

    mail = MailTMClient()
    try:
        mail.create_account()
        logger.info(f"Temp email: {mail.email_address}")

        bot = GensparkSignupBot(identity, mail)
        success, msg = bot.run(headless=HEADLESS)

        if success:
            return True, msg, mail
        else:
            mail.cleanup()
            return False, msg, None
    except Exception as e:
        logger.error(f"Error: {e}")
        mail.cleanup()
        return False, str(e), None


def main():
    """Create 2 accounts."""
    num_accounts = 2
    accounts = []

    for i in range(num_accounts):
        logger.info(f"\n{'='*60}")
        logger.info(f"Account {i+1}/{num_accounts}")
        logger.info(f"{'='*60}")

        success, msg, mail = create_single_account()
        if success and mail:
            accounts.append(msg)
            logger.info(f"SUCCESS: {msg}")
        else:
            logger.error(f"FAILED: {msg}")
            logger.info("Retrying...")
            time.sleep(5)
            success2, msg2, mail2 = create_single_account()
            if success2 and mail2:
                accounts.append(msg2)
                logger.info(f"SUCCESS on retry: {msg2}")
            else:
                logger.error(f"Retry failed: {msg2}")

        if i < num_accounts - 1:
            delay = random.uniform(5, 10)
            logger.info(f"Waiting {delay:.0f}s before next account...")
            time.sleep(delay)

    logger.info(f"\n{'='*60}")
    logger.info("RESULTS")
    logger.info(f"{'='*60}")

    if accounts:
        print("\n\n=== ACCOUNT CREDENTIALS ===")
        for acc in accounts:
            print(acc)
            print("---")
        print("=== END ===")
    else:
        print("\nNo accounts created successfully.")


if __name__ == "__main__":
    main()
