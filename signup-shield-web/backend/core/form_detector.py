# =============================================================================
# FORM AUTO-DETECTION & FILLING
# Automatically detects and fills signup form fields
# =============================================================================

import asyncio
import json
import logging
import aiohttp
from typing import Dict, List, Optional, Tuple

from core.captcha_solver_open import OpenCaptchaSolver, solve_captcha_open_source

logger = logging.getLogger(__name__)


class FormDetector:
    """Automatically detects and fills signup form fields on web pages."""

    # Field selectors in priority order
    FIELD_SELECTORS = {
        "full_name": [
            'input[name*="name"]:not([name*="user"]):not([name*="first"]):not([name*="last"])',
            'input[id*="name"]:not([id*="user"]):not([id*="first"]):not([id*="last"])',
            'input[placeholder*="name" i]:not([placeholder*="user" i]):not([placeholder*="first" i]):not([placeholder*="last" i])',
            'input[name*="full"]',
            'input[id*="full"]',
            'input[autocomplete="name"]',
        ],
        "first_name": [
            'input[name*="first"]:not([type="hidden"])',
            'input[id*="first"]:not([type="hidden"])',
            'input[placeholder*="first" i]:not([type="hidden"])',
            'input[name*="fname"]',
            'input[id*="fname"]',
            'input[autocomplete="given-name"]',
            'input[name*="first_name"]',
            'input[id*="first_name"]',
        ],
        "last_name": [
            'input[name*="last"]:not([type="hidden"]):not([name*="email"])',
            'input[id*="last"]:not([type="hidden"]):not([id*="email"])',
            'input[placeholder*="last" i]:not([type="hidden"])',
            'input[name*="lname"]',
            'input[id*="lname"]',
            'input[autocomplete="family-name"]',
            'input[name*="last_name"]',
            'input[id*="last_name"]',
        ],
        "email": [
            'input[type="email"]',
            'input[name*="email"]',
            'input[id*="email"]',
            'input[placeholder*="email" i]',
            'input[autocomplete="email"]',
            'input[name*="e-mail"]',
            'input[id*="e-mail"]',
        ],
        "password": [
            'input[type="password"]:not([name*="confirm"]):not([name*="current"])',
            'input[name*="password"]:not([name*="confirm"]):not([name*="current"])',
            'input[id*="password"]:not([id*="confirm"]):not([id*="current"])',
            'input[placeholder*="password" i]:not([placeholder*="confirm" i]):not([placeholder*="current" i])',
            'input[autocomplete="new-password"]',
            'input[name*="pass"]:not([name*="confirm"])',
            'input[id*="pass"]:not([id*="confirm"])',
        ],
        "confirm_password": [
            'input[type="password"][name*="confirm"]',
            'input[type="password"][id*="confirm"]',
            'input[type="password"][name*="password2"]',
            'input[type="password"][id*="password2"]',
            'input[type="password"][placeholder*="confirm" i]',
            'input[type="password"][name*="verification"]',
            'input[autocomplete="new-password"]:not(:first-of-type)',
        ],
        "phone": [
            'input[type="tel"]',
            'input[name*="phone"]',
            'input[name*="mobile"]',
            'input[name*="contact"]',
            'input[id*="phone"]',
            'input[id*="mobile"]',
            'input[placeholder*="phone" i]',
            'input[placeholder*="mobile" i]',
            'input[autocomplete="tel"]',
            'input[name*="phonenumber"]',
            'input[name*="phone_number"]',
        ],
        "username": [
            'input[name*="user"]',
            'input[id*="user"]',
            'input[placeholder*="user" i]',
            'input[name*="login"]',
            'input[id*="login"]',
            'input[name*="account"]',
            'input[autocomplete="username"]',
        ],
        "dob": [
            'input[type="date"]',
            'input[name*="dob"]',
            'input[name*="birth"]',
            'input[id*="dob"]',
            'input[id*="birth"]',
            'input[placeholder*="birth" i]',
            'input[name*="date_of_birth"]',
            'input[autocomplete="bday"]',
        ],
        "pincode": [
            'input[name*="pin"]',
            'input[name*="zip"]',
            'input[name*="postal"]',
            'input[id*="pin"]',
            'input[id*="zip"]',
            'input[placeholder*="pin" i]',
            'input[placeholder*="zip" i]',
            'input[autocomplete="postal-code"]',
        ],
    }

    SUBMIT_SELECTORS = [
        'button[type="submit"]',
        'input[type="submit"]',
        'button:has-text("Sign Up")',
        'button:has-text("Register")',
        'button:has-text("Create")',
        'button:has-text("Join")',
        'button:has-text("Submit")',
        'button:has-text("Get Started")',
        'button:has-text("Continue")',
        'button:has-text("Next")',
        '[class*="submit"]:not([class*="resubmit"])',
        '[id*="submit"]',
        'button[class*="signup"]',
        'button[class*="register"]',
        'button[id*="signup"]',
        'button[id*="register"]',
    ]

    CAPTCHA_SELECTORS = [
        'iframe[src*="recaptcha"]',
        'iframe[src*="hcaptcha"]',
        'iframe[src*="turnstile"]',
        '.g-recaptcha',
        '.h-captcha',
        '.cf-turnstile',
        '#captcha',
        '[class*="captcha"]',
        'iframe[src*="google.com/recaptcha"]',
        'iframe[src*="hcaptcha.com"]',
        'div[data-sitekey]',
    ]

    def __init__(self, page):
        self.page = page
        self.detected_fields: Dict[str, Optional[str]] = {}
        self.submit_button: Optional[str] = None
        self.captcha_detected = False
        self.captcha_type: Optional[str] = None
        self.captcha_sitekey: Optional[str] = None

    async def detect_all_fields(self) -> Dict[str, Optional[str]]:
        """Detect all form fields on the page."""
        logger.info("Detecting form fields...")

        for field_name, selectors in self.FIELD_SELECTORS.items():
            element = await self._find_element(selectors)
            if element:
                # Get a unique selector for the element
                selector = await self._get_selector_for_element(element)
                self.detected_fields[field_name] = selector
                logger.info(f"  Found {field_name}: {selector}")
            else:
                self.detected_fields[field_name] = None

        # Detect submit button
        submit_element = await self._find_element(self.SUBMIT_SELECTORS)
        if submit_element:
            self.submit_button = await self._get_selector_for_element(submit_element)
            logger.info(f"  Found submit button: {self.submit_button}")

        # Detect CAPTCHA
        await self._detect_captcha()

        return self.detected_fields

    async def _find_element(self, selectors: List[str]):
        """Find an element using multiple selector strategies."""
        for selector in selectors:
            try:
                if ":has-text(" in selector:
                    # Handle text-based selectors
                    text = selector.split(':has-text("')[1].split('")')[0]
                    css_selector = selector.split(':has-text(')[0] or "button"
                    elements = await self.page.query_selector_all(css_selector)
                    for element in elements:
                        element_text = await element.inner_text()
                        if text.lower() in element_text.lower():
                            return element
                else:
                    element = await self.page.query_selector(selector)
                    if element:
                        return element
            except Exception as e:
                logger.debug(f"Selector failed: {selector} - {e}")
                continue
        return None

    async def _get_selector_for_element(self, element) -> str:
        """Get the best selector for an element."""
        try:
            # Try to get id
            element_id = await element.get_attribute("id")
            if element_id:
                return f"#{element_id}"

            # Try to get name
            element_name = await element.get_attribute("name")
            if element_name:
                return f'[name="{element_name}"]'

            # Fallback to selector from query
            return await self.page.evaluate(
                """element => {
                    const tag = element.tagName.toLowerCase();
                    const type = element.type ? `[type="${element.type}"]` : '';
                    const classes = element.className && typeof element.className === 'string'
                        ? '.' + element.className.split(' ').filter(c => c).join('.')
                        : '';
                    return `${tag}${type}${classes}`;
                }""",
                element
            )
        except Exception:
            return "unknown"

    async def _detect_captcha(self):
        """Detect if CAPTCHA is present on the page and extract sitekey."""
        for selector in self.CAPTCHA_SELECTORS:
            try:
                element = await self.page.query_selector(selector)
                if element:
                    self.captcha_detected = True
                    if "recaptcha" in selector or "google.com/recaptcha" in selector:
                        self.captcha_type = "reCAPTCHA"
                    elif "hcaptcha" in selector or "hcaptcha.com" in selector:
                        self.captcha_type = "hCaptcha"
                    elif "turnstile" in selector:
                        self.captcha_type = "Cloudflare Turnstile"
                    else:
                        self.captcha_type = "Generic CAPTCHA"

                    # Extract sitekey from data-sitekey attribute or iframe src
                    self.captcha_sitekey = await self._extract_sitekey_from_element(element)
                    logger.warning(f"  CAPTCHA detected: {self.captcha_type} (sitekey: {self.captcha_sitekey})")
                    return
            except Exception:
                continue

    async def _extract_sitekey_from_element(self, element) -> Optional[str]:
        """Extract sitekey from a CAPTCHA element."""
        try:
            # Check for data-sitekey attribute
            sitekey = await element.get_attribute("data-sitekey")
            if sitekey:
                return sitekey

            # Check for iframe src
            src = await element.get_attribute("src")
            if src:
                # Parse from src URL
                from urllib.parse import parse_qs, urlparse
                parsed = urlparse(src)
                params = parse_qs(parsed.query)
                for key in ["k", "sitekey", "key"]:
                    if key in params and params[key]:
                        return params[key][0]

            # Try to find sitekey via JavaScript
            sitekey = await self.page.evaluate("""
                () => {
                    const el = document.querySelector('.g-recaptcha, .h-captcha, [data-sitekey]');
                    if (el) return el.getAttribute('data-sitekey');
                    // Check for grecaptcha render parameter
                    const recaptcha = document.querySelector('script[src*="recaptcha"]');
                    if (recaptcha) {
                        const match = recaptcha.src.match(/[?&]render=([^&]+)/);
                        if (match) return match[1];
                    }
                    return null;
                }
            """)
            return sitekey
        except Exception as e:
            logger.debug(f"Error extracting sitekey: {e}")
            return None

    async def extract_sitekey(self) -> Optional[str]:
        """
        Public method to detect and extract CAPTCHA sitekey from the page.
        Returns the sitekey string or None if not found.
        """
        await self._detect_captcha()
        return self.captcha_sitekey

    async def solve_captcha(self, api_key: str = "", service: str = "capsolver", page_url: str = "") -> bool:
        """
        Solve CAPTCHA using external service or open-source solver.

        Args:
            api_key: API key for paid services (capsolver/2captcha). 
                     If empty, uses open-source free solver.
            service: "capsolver", "2captcha", or "free" for open-source
            page_url: URL of the page where CAPTCHA is present

        Returns:
            True if CAPTCHA was solved and token injected successfully
        """
        if not self.captcha_detected:
            logger.info("No CAPTCHA detected, nothing to solve")
            return True

        # If no API key or service is "free", use open-source solver
        if not api_key or service.lower() == "free":
            logger.info("Using open-source CAPTCHA solver (no API key needed)")
            solver = OpenCaptchaSolver(self.page)
            result = await solver.solve(captcha_type=self.captcha_type)
            if result:
                logger.info("Open-source CAPTCHA solved successfully!")
                return True
            logger.warning("Open-source CAPTCHA solving failed")
            return False

        # Ensure we have a sitekey for paid services
        sitekey = self.captcha_sitekey
        if not sitekey:
            sitekey = await self.extract_sitekey()
        if not sitekey:
            logger.warning("Could not extract CAPTCHA sitekey")
            return False

        target_url = page_url or self.page.url
        logger.info(f"Solving {self.captcha_type} CAPTCHA via {service} (sitekey: {sitekey})")

        try:
            token = None
            if service.lower() == "capsolver":
                token = await self._solve_capsolver(api_key, sitekey, target_url)
            elif service.lower() == "2captcha":
                token = await self._solve_2captcha(api_key, sitekey, target_url)
            else:
                logger.error(f"Unknown CAPTCHA service: {service}")
                return False

            if token:
                return await self.inject_captcha_token(token)
            return False
        except Exception as e:
            logger.error(f"CAPTCHA solving failed: {e}")
            return False

    async def _solve_capsolver(self, api_key: str, sitekey: str, page_url: str) -> Optional[str]:
        """Solve CAPTCHA via Capsolver API."""
        task_type = "ReCaptchaV2TaskProxyless"
        if self.captcha_type == "hCaptcha":
            task_type = "HCaptchaTaskProxyless"
        elif self.captcha_type == "Cloudflare Turnstile":
            task_type = "AntiTurnstileTaskProxyless"

        async with aiohttp.ClientSession() as session:
            # Create task
            create_payload = {
                "clientKey": api_key,
                "task": {
                    "type": task_type,
                    "websiteURL": page_url,
                    "websiteKey": sitekey,
                }
            }

            if self.captcha_type == "hCaptcha":
                create_payload["task"]["type"] = "HCaptchaTaskProxyless"
            elif "turnstile" in (self.captcha_type or "").lower():
                create_payload["task"]["type"] = "AntiTurnstileTaskProxyless"

            try:
                async with session.post(
                    "https://api.capsolver.com/createTask",
                    json=create_payload,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as resp:
                    result = await resp.json()
                    if result.get("errorId") != 0:
                        logger.error(f"Capsolver create task error: {result.get('errorDescription', result)}")
                        return None
                    task_id = result.get("taskId")
                    if not task_id:
                        return None

                # Poll for result
                for _ in range(60):  # 60 * 5s = 5 min timeout
                    await asyncio.sleep(5)
                    async with session.post(
                        "https://api.capsolver.com/getTaskResult",
                        json={"clientKey": api_key, "taskId": task_id},
                        timeout=aiohttp.ClientTimeout(total=30)
                    ) as resp:
                        result = await resp.json()
                        status = result.get("status", "")
                        if status == "ready":
                            solution = result.get("solution", {})
                            token = solution.get("gRecaptchaResponse") or solution.get("token") or solution.get("captcha")
                            if token:
                                return token
                            logger.error(f"Capsolver solution missing token: {solution}")
                            return None
                        elif status == "failed":
                            logger.error(f"Capsolver task failed: {result}")
                            return None
                        # else "processing" — continue polling

                logger.error("Capsolver timeout - task did not complete")
                return None
            except Exception as e:
                logger.error(f"Capsolver API error: {e}")
                return None

    async def _solve_2captcha(self, api_key: str, sitekey: str, page_url: str) -> Optional[str]:
        """Solve CAPTCHA via 2captcha API."""
        method = "userrecaptcha"
        if self.captcha_type == "hCaptcha":
            method = "hcaptcha"
        elif "turnstile" in (self.captcha_type or "").lower():
            method = "turnstile"

        async with aiohttp.ClientSession() as session:
            try:
                # Submit CAPTCHA
                submit_url = "http://2captcha.com/in.php"
                params = {
                    "key": api_key,
                    "method": method,
                    "googlekey": sitekey,
                    "pageurl": page_url,
                    "json": 1,
                }
                async with session.get(submit_url, params=params, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                    result = await resp.json()
                    if result.get("status") != 1:
                        logger.error(f"2captcha submit error: {result}")
                        return None
                    captcha_id = result.get("request")

                # Poll for result
                poll_url = "http://2captcha.com/res.php"
                for _ in range(60):
                    await asyncio.sleep(5)
                    params = {
                        "key": api_key,
                        "action": "get",
                        "id": captcha_id,
                        "json": 1,
                    }
                    async with session.get(poll_url, params=params, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                        result = await resp.json()
                        if result.get("status") == 1:
                            return result.get("request")
                        elif result.get("request") != "CAPCHA_NOT_READY":
                            logger.error(f"2captcha error: {result}")
                            return None

                logger.error("2captcha timeout")
                return None
            except Exception as e:
                logger.error(f"2captcha API error: {e}")
                return None

    async def inject_captcha_token(self, token: str) -> bool:
        """
        Inject a solved CAPTCHA token into the page.
        Handles reCAPTCHA, hCaptcha, and generic CAPTCHA callbacks.
        """
        try:
            # Try grecaptcha first
            injected = await self.page.evaluate(f"""
                (token) => {{
                    // reCAPTCHA v2
                    if (typeof grecaptcha !== 'undefined' && grecaptcha.execute) {{
                        try {{
                            const widgets = document.querySelectorAll('[data-sitekey]');
                            widgets.forEach(w => {{
                                const widgetId = Number(w.getAttribute('data-recaptcha-widget-id'));
                                if (!isNaN(widgetId)) {{
                                    grecaptcha.enterprise?.ready?.(() => {{
                                        grecaptcha.enterprise.execute(widgetId);
                                    }});
                                }}
                            }});
                        }} catch(e) {{ console.log('grecaptcha exec err:', e); }}
                    }}

                    // Set textarea value (common reCAPTCHA pattern)
                    const textareas = document.querySelectorAll('textarea[name="g-recaptcha-response"]');
                    textareas.forEach(ta => {{
                        ta.innerHTML = token;
                        ta.value = token;
                        ta.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        ta.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    }});

                    // hCaptcha
                    if (typeof hcaptcha !== 'undefined') {{
                        try {{
                            hcaptcha.render(document.querySelector('.h-captcha'), {{
                                sitekey: document.querySelector('.h-captcha')?.getAttribute('data-sitekey'),
                            }});
                        }} catch(e) {{ console.log('hcaptcha err:', e); }}
                    }}

                    // Find and fire __cf_chl_frm or turnstile callbacks
                    document.querySelectorAll('input[name="cf-turnstile-response"], input[name="captcha"]').forEach(el => {{
                        el.value = token;
                        el.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        el.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    }});

                    return true;
                }}
            """, token)

            # Also try executing any captcha callback
            await self.page.evaluate(f"""
                (token) => {{
                    // Try to find __doPostBack or similar
                    const allScripts = document.scripts;
                    for (let s of allScripts) {{
                        if (s.text.includes('g-recaptcha-response') || s.text.includes('captcha')) {{
                            // Script likely handles captcha — let it process
                        }}
                    }}
                    // Dispatch a custom event some frameworks listen for
                    window.dispatchEvent(new CustomEvent('captchaSolved', {{ detail: token }}));
                    return true;
                }}
            """, token)

            await asyncio.sleep(1)
            logger.info("CAPTCHA token injected successfully")
            return True
        except Exception as e:
            logger.error(f"Error injecting CAPTCHA token: {e}")
            return False

    async def detect_multi_step_form(self) -> bool:
        """
        Detect if the form has multiple steps (Next/Continue buttons).
        Returns True if multi-step form detected.
        """
        try:
            # Look for next/continue buttons that are not submit
            multi_step_selectors = [
                'button:has-text("Next")',
                'button:has-text("Continue")',
                'button:has-text("Next Step")',
                '[class*="next"]:not([class*="next-"])',
                '[class*="step"]:not([class*="stepper"])',
                'a:has-text("Next")',
                'button[aria-label*="next" i]',
            ]

            for selector in multi_step_selectors:
                try:
                    if ":has-text(" in selector:
                        text = selector.split(':has-text("')[1].split('")')[0]
                        css_selector = selector.split(':has-text(')[0] or "button"
                        elements = await self.page.query_selector_all(css_selector)
                        for element in elements:
                            element_text = await element.inner_text()
                            if text.lower() in element_text.lower():
                                logger.info(f"Multi-step form detected: '{text}' button found")
                                return True
                    else:
                        element = await self.page.query_selector(selector)
                        if element and await element.is_visible():
                            logger.info(f"Multi-step form detected: '{selector}'")
                            return True
                except Exception:
                    continue

            # Check for multi-step indicators in form structure
            has_steps = await self.page.evaluate("""
                () => {
                    // Check for step indicators
                    const indicators = document.querySelectorAll('[class*="step"], [class*="progress"], [aria-current="step"]');
                    if (indicators.length > 1) return true;

                    // Check for hidden fields that suggest multiple pages
                    const hiddenDivs = document.querySelectorAll('div[style*="display: none"], div[hidden]');
                    if (hiddenDivs.length > 3) return true;

                    // Check for tab panels
                    const tabpanels = document.querySelectorAll('[role="tabpanel"]');
                    if (tabpanels.length > 1) return true;

                    return false;
                }
            """)

            if has_steps:
                logger.info("Multi-step form detected (via structure indicators)")
                return True

            return False
        except Exception as e:
            logger.debug(f"Error detecting multi-step form: {e}")
            return False

    def get_field_summary(self) -> Dict:
        """Get a summary of detected fields."""
        total_fields = len([f for f in self.detected_fields.values() if f is not None])
        return {
            "total_detected": total_fields,
            "fields": self.detected_fields,
            "submit_button": self.submit_button,
            "captcha_detected": self.captcha_detected,
            "captcha_type": self.captcha_type,
        }

    async def fill_field(self, field_name: str, value: str) -> bool:
        """Fill a detected field with a value."""
        selector = self.detected_fields.get(field_name)
        if not selector:
            logger.warning(f"Field {field_name} not detected, skipping")
            return False

        try:
            element = await self.page.query_selector(selector)
            if not element:
                return False

            await element.fill("")
            await element.fill(value)
            logger.info(f"  Filled {field_name}")
            return True
        except Exception as e:
            logger.error(f"  Error filling {field_name}: {e}")
            return False

    async def click_submit(self) -> bool:
        """Click the submit button."""
        if not self.submit_button:
            logger.warning("Submit button not detected")
            return False

        try:
            element = await self.page.query_selector(self.submit_button)
            if not element:
                # Try fallback selectors
                for selector in self.SUBMIT_SELECTORS:
                    try:
                        element = await self.page.query_selector(selector)
                        if element:
                            break
                    except Exception:
                        continue

            if element:
                await element.click()
                logger.info("  Clicked submit button")
                return True
            return False
        except Exception as e:
            logger.error(f"  Error clicking submit: {e}")
            return False

    async def fill_form(self, identity: Dict) -> List[str]:
        """
        Fill the form with identity data.

        Returns:
            List of successfully filled field names
        """
        filled_fields = []

        # Determine if form has separate first/last name or full name
        has_first = self.detected_fields.get("first_name") is not None
        has_last = self.detected_fields.get("last_name") is not None
        has_full = self.detected_fields.get("full_name") is not None

        if has_first and has_last:
            if await self.fill_field("first_name", identity["name"]["first"]):
                filled_fields.append("first_name")
            if await self.fill_field("last_name", identity["name"]["last"]):
                filled_fields.append("last_name")
        elif has_full:
            if await self.fill_field("full_name", identity["name"]["full"]):
                filled_fields.append("full_name")
        elif has_first:
            # Only first name field found
            if await self.fill_field("first_name", identity["name"]["first"]):
                filled_fields.append("first_name")

        # Fill other fields
        field_mapping = {
            "email": identity["email"],
            "password": identity["password"],
            "confirm_password": identity["password"],
            "phone": identity["phone"],
            "username": identity["email"].split("@")[0],
            "dob": identity["dob"],
            "pincode": identity["location"]["pincode"],
        }

        for field_name, value in field_mapping.items():
            if await self.fill_field(field_name, value):
                filled_fields.append(field_name)

        return filled_fields

    async def check_field_validations(self) -> Dict[str, Dict]:
        """Check HTML5 validation attributes on detected fields."""
        validations = {}

        for field_name, selector in self.detected_fields.items():
            if not selector:
                continue

            try:
                element = await self.page.query_selector(selector)
                if not element:
                    continue

                attrs = await self.page.evaluate(
                    """element => ({
                        required: element.required,
                        minLength: element.minLength,
                        maxLength: element.maxLength,
                        pattern: element.pattern,
                        type: element.type,
                        autocomplete: element.autocomplete,
                    })""",
                    element
                )
                validations[field_name] = attrs
            except Exception:
                continue

        return validations
