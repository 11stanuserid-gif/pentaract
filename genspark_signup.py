#!/usr/bin/env python3
"""
Genspark.ai Signup Automation Script
Targeted signup bot for genspark.ai with full anti-detection.
"""

import asyncio
import json
import logging
import random
import string
import sys
import time
from datetime import datetime
from typing import Dict, List, Optional

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("genspark-signup")

# ============================================================
# Identity Generator (fixed — ensures truly unique emails)
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

# 10+ different email domains to avoid domain-based blocking
EMAIL_DOMAINS = [
    "gmail.com", "yahoo.com", "outlook.com", "hotmail.com",
    "rediffmail.com", "icloud.com", "protonmail.com",
    "zoho.com", "yandex.com", "gmx.com",
    "fastmail.com", "aol.com", "live.com", "msn.com",
    "tutanota.com", "hushmail.com", "keemail.me",
]

class IdentityGenerator:
    def __init__(self):
        self._used_emails = set()
        self._used_names = set()
        self._domain_index = 0  # rotate domains evenly

    def _next_domain(self) -> str:
        domain = EMAIL_DOMAINS[self._domain_index % len(EMAIL_DOMAINS)]
        self._domain_index += 1
        return domain

    def generate_identity(self) -> Dict:
        # Name
        first = random.choice(FIRST_NAMES)
        last = random.choice(LAST_NAMES)
        full_name = f"{first} {last}"
        while full_name in self._used_names:
            first = random.choice(FIRST_NAMES)
            last = random.choice(LAST_NAMES)
            full_name = f"{first} {last}"
        self._used_names.add(full_name)

        # Email — use unique timestamp + random suffix with different domains
        ts = int(time.time() * 1000) % 10000000
        rnd = random.randint(1000, 9999)
        domain = self._next_domain()
        email = f"user{ts}_{rnd}@{domain}"
        while email in self._used_emails:
            rnd = random.randint(1000, 9999)
            domain = self._next_domain()
            email = f"user{ts}_{rnd}@{domain}"
        self._used_emails.add(email)

        # Password — completely random, no pattern
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
# Stealth Scripts
# ============================================================

STEALTH_SCRIPTS = [
    """Object.defineProperty(navigator, 'webdriver', { get: () => undefined });""",
    """delete navigator.__proto__.webdriver;""",
    """Object.defineProperty(navigator, 'plugins', { get: () => [1,2,3,4,5] });""",
    """Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });""",
    """
    const originalGetParameter = WebGLRenderingContext.prototype.getParameter;
    WebGLRenderingContext.prototype.getParameter = function(p) {
        if (p === 37445) return 'Intel Inc.';
        if (p === 37446) return 'Intel Iris OpenGL Engine';
        return originalGetParameter.apply(this, arguments);
    };
    """,
    """
    const originalGetImageData = CanvasRenderingContext2D.prototype.getImageData;
    CanvasRenderingContext2D.prototype.getImageData = function(x, y, w, h) {
        const imageData = originalGetImageData.call(this, x, y, w, h);
        for (let i = 0; i < imageData.data.length; i += 4) {
            imageData.data[i] += (Math.random() < 0.5 ? -1 : 1);
        }
        return imageData;
    };
    """,
]


# ============================================================
# Main Signup Function
# ============================================================

async def try_signup(identity: Dict, account_num: int) -> bool:
    """
    Attempt to sign up on genspark.ai with the given identity.
    Returns True if successful.
    """
    from playwright.async_api import async_playwright

    email = identity["email"]
    password = identity["password"]
    full_name = identity["full_name"]
    first_name = identity["first_name"]
    last_name = identity["last_name"]

    logger.info(f"[Account {account_num}] Attempting signup: {email} / {password}")

    pw = await async_playwright().start()
    success = False
    page = None

    try:
        # Launch browser with stealth args
        browser = await pw.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--window-size=1920,1080",
            ],
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

        # Apply stealth init scripts
        for script in STEALTH_SCRIPTS:
            await context.add_init_script(script)

        page = await context.new_page()

        # Navigate to genspark
        logger.info(f"[Account {account_num}] Navigating to genspark.ai...")
        try:
            await page.goto("https://www.genspark.ai/", wait_until="domcontentloaded", timeout=60000)
        except Exception as e:
            logger.warning(f"[Account {account_num}] Initial nav issue: {e}")
        
        await asyncio.sleep(3)

        # Check if we hit Cloudflare challenge
        page_title = await page.title()
        logger.info(f"[Account {account_num}] Page title: {page_title}")

        if "Just a moment" in page_title or "challenge" in page_title.lower():
            logger.info(f"[Account {account_num}] Cloudflare challenge detected, waiting...")
            await asyncio.sleep(5)
            # Wait for challenge to pass
            for i in range(20):
                await asyncio.sleep(2)
                try:
                    new_title = await page.title()
                    if "Just a moment" not in new_title and "challenge" not in new_title.lower():
                        logger.info(f"[Account {account_num}] Cloudflare challenge passed!")
                        break
                except:
                    pass
                logger.info(f"[Account {account_num}] Still waiting for CF challenge... ({i+1}/20)")

        # Now we should be on genspark. Look for signup/login buttons
        await asyncio.sleep(2)

        # Take a screenshot to see what we're dealing with
        await page.screenshot(path=f"/opt/render/reports/genspark_{account_num}_initial.png", full_page=True)
        logger.info(f"[Account {account_num}] Screenshot saved")

        # Try to find and click signup button
        signup_clicked = False
        signup_selectors = [
            'a[href*="signup"]',
            'a[href*="register"]',
            'a[href*="sign-up"]',
            'button:has-text("Sign Up")',
            'button:has-text("Sign up")',
            'button:has-text("Register")',
            'button:has-text("Get Started")',
            'a:has-text("Sign Up")',
            'a:has-text("Sign up")',
            'a:has-text("Register")',
            '[class*="signup"]',
            '[class*="sign-up"]',
            '[class*="register"]',
        ]

        for sel in signup_selectors:
            try:
                el = await page.query_selector(sel)
                if el and await el.is_visible():
                    logger.info(f"[Account {account_num}] Clicking signup button: {sel}")
                    await el.click()
                    await asyncio.sleep(3)
                    signup_clicked = True
                    break
            except:
                continue

        # If no signup button found, maybe there's a login page with email/password fields already
        if not signup_clicked:
            logger.info(f"[Account {account_num}] No signup button found, checking for form fields...")

        # Check the current URL
        current_url = page.url
        logger.info(f"[Account {account_num}] Current URL: {current_url}")

        # Try to navigate directly to signup page
        if not signup_clicked:
            try:
                await page.goto("https://www.genspark.ai/signup", wait_until="domcontentloaded", timeout=30000)
                await asyncio.sleep(3)
                logger.info(f"[Account {account_num}] Navigated to /signup, URL: {page.url}")
            except Exception as e:
                logger.warning(f"[Account {account_num}] /signup nav failed: {e}")

        # Take screenshot after navigation
        await page.screenshot(path=f"/opt/render/reports/genspark_{account_num}_signup_page.png", full_page=True)

        # Detect form fields
        await asyncio.sleep(2)

        # Look for email field
        email_filled = False
        email_selectors = [
            'input[type="email"]',
            'input[name*="email"]',
            'input[id*="email"]',
            'input[placeholder*="email" i]',
            'input[autocomplete="email"]',
        ]

        for sel in email_selectors:
            try:
                el = await page.query_selector(sel)
                if el and await el.is_visible():
                    logger.info(f"[Account {account_num}] Found email field: {sel}")
                    await el.click()
                    await asyncio.sleep(0.5)
                    await el.fill(email)
                    logger.info(f"[Account {account_num}] Filled email: {email}")
                    email_filled = True
                    break
            except:
                continue

        # Look for password field
        password_filled = False
        password_selectors = [
            'input[type="password"]',
            'input[name*="password"]',
            'input[id*="password"]',
            'input[placeholder*="password" i]',
            'input[autocomplete*="password"]',
            'input[autocomplete="new-password"]',
        ]

        for sel in password_selectors:
            try:
                el = await page.query_selector(sel)
                if el and await el.is_visible():
                    logger.info(f"[Account {account_num}] Found password field: {sel}")
                    await el.click()
                    await asyncio.sleep(0.3)
                    await el.fill(password)
                    logger.info(f"[Account {account_num}] Filled password")
                    password_filled = True
                    break
            except:
                continue

        # Look for name field
        name_filled = False
        name_selectors = [
            'input[name*="name"]',
            'input[id*="name"]',
            'input[placeholder*="name" i]',
            'input[autocomplete="name"]',
            'input[autocomplete="given-name"]',
        ]

        for sel in name_selectors:
            try:
                el = await page.query_selector(sel)
                if el and await el.is_visible():
                    logger.info(f"[Account {account_num}] Found name field: {sel}")
                    await el.click()
                    await asyncio.sleep(0.3)
                    await el.fill(full_name)
                    name_filled = True
                    break
            except:
                continue

        # Look for submit/signup/continue button
        submit_clicked = False
        submit_selectors = [
            'button[type="submit"]',
            'input[type="submit"]',
            'button:has-text("Sign Up")',
            'button:has-text("Sign up")',
            'button:has-text("Sign Up Free")',
            'button:has-text("Continue")',
            'button:has-text("Next")',
            'button:has-text("Create Account")',
            'button:has-text("Register")',
            'button:has-text("Get Started")',
            '[class*="submit"]',
            '[id*="submit"]',
        ]

        for sel in submit_selectors:
            try:
                el = await page.query_selector(sel)
                if el and await el.is_visible():
                    logger.info(f"[Account {account_num}] Clicking submit: {sel}")
                    await el.click()
                    submit_clicked = True
                    await asyncio.sleep(3)
                    break
            except:
                continue

        # If nothing found, maybe it's a multi-step or different flow
        if not (email_filled or password_filled or name_filled):
            logger.warning(f"[Account {account_num}] No form fields detected. Saving page content...")
            content = await page.content()
            with open(f"/opt/render/reports/genspark_{account_num}_page.html", "w") as f:
                f.write(content[:10000])
            # Check what's on the page
            logger.warning(f"[Account {account_num}] Page content length: {len(content)}")
            
            # Maybe the page uses a different signup flow — check for Google/SSO buttons
            sso_selectors = [
                'button:has-text("Google")',
                'button:has-text("google")',
                'button:has-text("Continue with Google")',
                'a[href*="google"]',
            ]
            for sel in sso_selectors:
                try:
                    el = await page.query_selector(sel)
                    if el and await el.is_visible():
                        logger.info(f"[Account {account_num}] Found Google SSO button")
                        break
                except:
                    continue

        # Take final screenshot
        await page.screenshot(path=f"/opt/render/reports/genspark_{account_num}_final.png", full_page=True)

        # Check for success
        await asyncio.sleep(2)
        final_url = page.url
        final_title = await page.title()
        content_lower = (await page.content()).lower()

        success_indicators = [
            "welcome", "dashboard", "account", "home", "profile",
            "verify", "verification sent", "check your email",
            "thank you", "signed up", "success", "joined",
        ]

        blocked_indicators = [
            "error", "invalid", "already exists", "already taken",
            "captcha", "robot", "blocked", "denied", "try again",
        ]

        success_score = sum(1 for ind in success_indicators if ind in content_lower)
        blocked_score = sum(1 for ind in blocked_indicators if ind in content_lower)

        logger.info(f"[Account {account_num}] Final URL: {final_url}")
        logger.info(f"[Account {account_num}] Final title: {final_title}")
        logger.info(f"[Account {account_num}] Success indicators: {success_score}, Blocked: {blocked_score}")

        if success_score >= 2 or final_url != "https://www.genspark.ai/" and final_url != "about:blank":
            if blocked_score == 0:
                success = True
                logger.info(f"[Account {account_num}] SIGNUP SUCCESSFUL!")
            elif success_score > blocked_score:
                success = True
                logger.info(f"[Account {account_num}] Signup likely successful (s:{success_score} b:{blocked_score})")
            else:
                logger.warning(f"[Account {account_num}] Ambiguous result (s:{success_score} b:{blocked_score})")
        else:
            logger.warning(f"[Account {account_num}] Signup blocked or failed")

        if success:
            logger.info(f"=== ACCOUNT {account_num} ===")
            logger.info(f"Email:    {email}")
            logger.info(f"Password: {password}")

    except Exception as e:
        logger.error(f"[Account {account_num}] Error: {e}", exc_info=True)

    finally:
        try:
            if page:
                await context.close()
            await browser.close()
            await pw.stop()
        except:
            pass

    return success, email, password


async def main():
    num_accounts = 2
    identity_gen = IdentityGenerator()
    
    accounts = []
    
    for i in range(num_accounts):
        identity = identity_gen.generate_identity()
        logger.info(f"\n{'='*60}")
        logger.info(f"Starting account {i+1}/{num_accounts}")
        logger.info(f"Email: {identity['email']}")
        logger.info(f"Password: {identity['password']}")
        logger.info(f"Name: {identity['full_name']}")
        logger.info(f"{'='*60}\n")

        success, email, password = await try_signup(identity, i+1)
        
        if success:
            accounts.append({"email": email, "password": password})
        else:
            logger.warning(f"Account {i+1} failed")

        if i < num_accounts - 1:
            delay = random.uniform(5, 15)
            logger.info(f"Waiting {delay:.1f}s before next account...")
            await asyncio.sleep(delay)

    # Print results
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
