# =============================================================================
# SIGNUP BOT ENGINE
# Attempts to successfully sign up accounts on target websites.
# Features: CAPTCHA solving, email verification, device fingerprint rotation,
# proxy rotation, identity generation, credential capture
# =============================================================================

import asyncio
import json
import logging
import random
import time
from datetime import datetime
from typing import Dict, List, Optional

from core.identity_generator import IdentityGenerator
from core.fingerprint_generator import FingerprintGenerator
from core.form_detector import FormDetector
from core.behavior_simulator import BehaviorSimulator
from core.browser_manager import BrowserManager
from core.email_verifier import EmailVerifier

logger = logging.getLogger(__name__)


class SecurityTestResult:
    """Stores the result of a single security test."""

    def __init__(self, test_name: str, passed: bool, details: Dict = None, screenshot_path: str = None):
        self.test_name = test_name
        self.passed = passed  # True = security feature worked (blocked/threat detected)
        self.details = details or {}
        self.screenshot_path = screenshot_path
        self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> Dict:
        return {
            "test_name": self.test_name,
            "passed": self.passed,
            "details": self.details,
            "screenshot_path": self.screenshot_path,
            "timestamp": self.timestamp,
        }


class SignupAttempt:
    """Records a single signup attempt."""

    def __init__(self, attempt_number: int, identity: Dict, fingerprint: Dict):
        self.attempt_number = attempt_number
        self.identity = identity
        self.fingerprint = fingerprint
        self.timestamp = datetime.now().isoformat()
        self.success = False
        self.error_message = None
        self.response_url = None
        self.page_title = None
        self.fields_filled = []
        self.security_results: List[SecurityTestResult] = []
        self.credentials = {}  # captured email + password on success
        self.temp_email_used = None
        self.captcha_solved = False
        self.email_verified = False

    def to_dict(self) -> Dict:
        return {
            "attempt_number": self.attempt_number,
            "timestamp": self.timestamp,
            "identity": {
                "name": self.identity["name"]["full"],
                "email": self.identity["email"],
                "phone": self.identity["phone"],
                "password": self.identity["password"],
                "location": f"{self.identity['location']['city']}, {self.identity['location']['state']}",
                "is_weak_password": self.identity.get("is_weak_password", False),
            },
            "fingerprint_summary": {
                "screen": f"{self.fingerprint['screen']['width']}x{self.fingerprint['screen']['height']}",
                "browser": self.fingerprint["browser"]["user_agent"][:60] + "...",
                "platform": self.fingerprint["browser"]["platform"],
                "ip": self.fingerprint.get("ip", "N/A"),
            },
            "success": self.success,
            "error_message": self.error_message,
            "response_url": self.response_url,
            "page_title": self.page_title,
            "fields_filled": self.fields_filled,
            "security_results": [r.to_dict() for r in self.security_results],
            "credentials": self.credentials,
            "temp_email_used": self.temp_email_used,
            "captcha_solved": self.captcha_solved,
            "email_verified": self.email_verified,
        }


class SecurityTester:
    """
    Signup automation engine.
    Attempts to successfully create accounts on target signup pages,
    with CAPTCHA solving, email verification, and anti-detection features.
    """

    def __init__(
        self,
        target_url: str,
        num_accounts: int = 1,
        delay_range: tuple = (2.0, 5.0),
        headless: bool = True,
        proxy_list: List[str] = None,
        test_captcha: bool = True,
        test_rate_limit: bool = True,
        test_email_verify: bool = True,
        test_fingerprint: bool = True,
        test_password_policy: bool = True,
        test_duplicate: bool = True,
        weak_password_ratio: float = 0.0,
        captcha_api_key: str = "",
        captcha_service: str = "capsolver",
    ):
        self.target_url = target_url
        self.num_accounts = num_accounts
        self.delay_range = delay_range
        self.headless = headless
        self.proxy_list = proxy_list or []
        self.current_proxy_index = 0

        # Test flags
        self.test_captcha = test_captcha
        self.test_rate_limit = test_rate_limit
        self.test_email_verify = test_email_verify
        self.test_fingerprint = test_fingerprint
        self.test_password_policy = test_password_policy
        self.test_duplicate = test_duplicate
        self.weak_password_ratio = weak_password_ratio

        # CAPTCHA solving config
        self.captcha_api_key = captcha_api_key
        self.captcha_service = captcha_service  # "capsolver" or "2captcha"

        # Generators
        self.identity_gen = IdentityGenerator()
        self.fingerprint_gen = FingerprintGenerator()
        self.email_verifier = EmailVerifier()

        # Results
        self.attempts: List[SignupAttempt] = []
        self.created_accounts: List[Dict] = []
        self.start_time = None
        self.end_time = None

    def get_next_proxy(self) -> Optional[str]:
        """Get the next proxy from the rotation list."""
        if not self.proxy_list:
            return None
        proxy = self.proxy_list[self.current_proxy_index % len(self.proxy_list)]
        self.current_proxy_index += 1
        return proxy

    async def run_all_tests(self, progress_callback=None) -> Dict:
        """
        Run all signup attempts with anti-detection and CAPTCHA solving.

        Args:
            progress_callback: Optional callback(current, total, message) for progress updates

        Returns:
            Complete results dictionary with created accounts
        """
        self.start_time = datetime.now()
        logger.info(f"Starting signup automation on: {self.target_url}")
        logger.info(f"Number of accounts: {self.num_accounts}")
        logger.info(f"CAPTCHA solving: {'ON (' + self.captcha_service + ')' if self.captcha_api_key else 'OFF'}")
        logger.info(f"Email verification: {'ON' if self.test_email_verify else 'OFF'}")
        logger.info(f"Tests: CAPTCHA={self.test_captcha}, RateLimit={self.test_rate_limit}, "
                   f"EmailVerify={self.test_email_verify}, Fingerprint={self.test_fingerprint}, "
                   f"PasswordPolicy={self.test_password_policy}, Duplicate={self.test_duplicate}")

        # Generate all identities upfront
        identities = self.identity_gen.generate_batch(
            self.num_accounts,
            weak_password_ratio=self.weak_password_ratio
        )

        if progress_callback:
            progress_callback(0, self.num_accounts, f"Generated identities, starting tests...")

        # Run signup attempts
        for i, identity in enumerate(identities):
            attempt_num = i + 1

            if progress_callback:
                progress_callback(attempt_num, self.num_accounts, f"Testing account {attempt_num}/{self.num_accounts}...")

            # Delay between signups (except first)
            if i > 0:
                delay = random.uniform(self.delay_range[0], self.delay_range[1])
                logger.info(f"Waiting {delay:.1f}s before next signup...")
                await asyncio.sleep(delay)

            # Run signup attempt with enhanced success focus
            attempt = await self._run_signup_attempt(attempt_num, identity)
            self.attempts.append(attempt)

            # If successful, capture credentials
            if attempt.success:
                creds = {
                    "email": attempt.credentials.get("email", identity["email"]),
                    "password": attempt.credentials.get("password", identity["password"]),
                    "name": identity["name"]["full"],
                    "phone": identity["phone"],
                    "verified": attempt.email_verified,
                    "attempt_number": attempt_num,
                    "timestamp": attempt.timestamp,
                }
                self.created_accounts.append(creds)
                logger.info(f"Account created: {creds['email']} / {creds['password']}")

            # Rate limit test (secondary, only if enabled)
            if self.test_rate_limit and i > 0 and self.delay_range[0] < 1.0:
                rate_result = self._analyze_rate_limit(attempt, self.attempts[i-1])
                attempt.security_results.append(rate_result)

        self.end_time = datetime.now()

        if progress_callback:
            progress_callback(self.num_accounts, self.num_accounts, "Tests complete! Generating report...")

        return self._compile_results()

    async def _run_signup_attempt(self, attempt_num: int, identity: Dict) -> SignupAttempt:
        """Run a single signup attempt with full anti-detection and CAPTCHA solving."""
        fingerprint = self.fingerprint_gen.generate_fingerprint()
        geolocation = {
            "latitude": identity["location"]["latitude"],
            "longitude": identity["location"]["longitude"],
        }
        fingerprint["geolocation"] = geolocation

        attempt = SignupAttempt(attempt_num, identity, fingerprint)
        proxy = self.get_next_proxy()

        # Create temp email only for verification inbox checking (does NOT replace identity email)
        temp_email_info = None
        if self.test_email_verify:
            try:
                temp_email_info = await self.email_verifier.create_verified_email()
                if "error" not in temp_email_info:
                    # Keep temp email only for verification inbox, use identity's own email (multi-domain) for form
                    attempt.temp_email_used = temp_email_info["email"]
                    logger.info(f"Temp email created (for verification): {temp_email_info['email']}")
                    logger.info(f"Using identity email (multi-domain): {identity['email']}")
                else:
                    logger.warning(f"Temp email creation failed: {temp_email_info.get('error')}")
            except Exception as e:
                logger.warning(f"Temp email error: {e}")

        browser_manager = BrowserManager(
            headless=self.headless,
            proxy=proxy
        )

        try:
            # Launch browser with unique fingerprint
            launched = await browser_manager.launch(fingerprint)
            if not launched:
                attempt.error_message = "Failed to launch browser"
                return attempt

            # Navigate to target
            navigated = await browser_manager.navigate(self.target_url)
            if not navigated:
                attempt.error_message = "Failed to navigate to target URL"
                return attempt

            # Wait for page to settle
            await asyncio.sleep(2)

            # Get page info
            attempt.page_title = await browser_manager.page.title()
            attempt.response_url = browser_manager.page.url

            # Initialize behavior simulator
            behavior = BehaviorSimulator(browser_manager.page)

            # Simulate human reading behavior
            await behavior.simulate_page_reading()

            # Detect form fields
            form_detector = FormDetector(browser_manager.page)
            detected_fields = await form_detector.detect_all_fields()

            # CAPTCHA Detection
            if self.test_captcha:
                captcha_result = form_detector.captcha_detected
                # Store detection result for analysis
                if captcha_result:
                    logger.info(f"CAPTCHA detected: {form_detector.captcha_type}")
                    # Try to solve CAPTCHA (with API key if provided, else open-source)
                    if self.captcha_api_key or True:  # Always attempt solving
                        solved = await form_detector.solve_captcha(
                            api_key=self.captcha_api_key or "",
                            service=self.captcha_service if self.captcha_api_key else "free",
                            page_url=browser_manager.page.url,
                        )
                        if solved:
                            attempt.captcha_solved = True
                            logger.info("CAPTCHA solved successfully!")
                        else:
                            logger.warning("CAPTCHA solving failed")

            # Fill form with human behavior
            await behavior.random_mouse_movement(num_points=random.randint(2, 4))

            # Fill the form with identity data
            filled_fields = await form_detector.fill_form(identity)
            attempt.fields_filled = filled_fields

            # Check for field validations (HTML5)
            validations = await form_detector.check_field_validations()

            # Password Policy Test (secondary analysis)
            if self.test_password_policy and identity.get("is_weak_password"):
                pw_result = await self._test_password_policy(browser_manager.page, form_detector, validations)
                attempt.security_results.append(pw_result)

            # Delay before submit
            await asyncio.sleep(random.uniform(1.0, 3.0))

            # Take pre-submit screenshot
            pre_submit_ss = f"reports/screenshot_attempt_{attempt_num}_pre_submit.png"
            await browser_manager.take_screenshot(pre_submit_ss)

            # Click submit
            submitted = await form_detector.click_submit()

            # Wait for response
            await asyncio.sleep(3)

            # Take post-submit screenshot
            post_submit_ss = f"reports/screenshot_attempt_{attempt_num}_post_submit.png"
            await browser_manager.take_screenshot(post_submit_ss)
            attempt.response_url = browser_manager.page.url

            # Analyze result — look for success signals
            success, message = await self._analyze_response(
                browser_manager.page, attempt, form_detector
            )
            attempt.success = success
            attempt.error_message = message

            # If signup seems successful, capture credentials
            if success:
                attempt.credentials = {
                    "email": identity["email"],
                    "password": identity["password"],
                }

                # Handle email verification if temp email was used
                if self.test_email_verify and temp_email_info and "token" in temp_email_info:
                    try:
                        verified = await self._verify_email_flow(
                            temp_email_info["token"],
                            browser_manager.page,
                            identity["email"],
                            identity["password"],
                        )
                        attempt.email_verified = verified
                    except Exception as e:
                        logger.error(f"Email verification error: {e}")
            else:
                # Try alternative submit methods if first attempt failed
                logger.info(f"Initial submit may have failed. Trying alternative methods...")
                alt_success = await self._try_alternative_submit(
                    browser_manager.page, form_detector, behavior, identity
                )
                if alt_success:
                    attempt.success = True
                    attempt.credentials = {
                        "email": identity["email"],
                        "password": identity["password"],
                    }
                    attempt.error_message = "Success after alternative submit"

            # Email Verification Analysis (keep as secondary)
            if self.test_email_verify:
                email_result = await self._test_email_verification(
                    browser_manager.page, attempt
                )
                attempt.security_results.append(email_result)

            # Duplicate Account Test (secondary)
            if self.test_duplicate and attempt_num > 1:
                dup_result = await self._test_duplicate_detection(
                    browser_manager.page, attempt
                )
                attempt.security_results.append(dup_result)

            logger.info(f"Attempt {attempt_num}: {'SUCCESS' if success else 'BLOCKED'} - {message}")

        except Exception as e:
            logger.error(f"Error in attempt {attempt_num}: {e}")
            attempt.error_message = str(e)

        finally:
            await browser_manager.close()

        return attempt

    async def _verify_email_flow(self, token: str, page, email: str, password: str) -> bool:
        """Handle full email verification flow after signup."""
        try:
            logger.info("Starting email verification flow...")
            result = await self.email_verifier.verify_email(
                token=token,
                page=page,
                timeout=120,
            )

            if result.get("email_verified"):
                self.email_verifier.add_verified_account(
                    email=email,
                    password=password,
                    verified=True,
                )
                logger.info(f"Email verified for {email}")
                return True
            elif result.get("verification_email_received"):
                # Link was extracted but verification unclear
                logger.warning(f"Verification email received but status unclear: {result.get('error')}")
                return False
            else:
                logger.warning(f"Verification email not received: {result.get('error')}")
                return False
        except Exception as e:
            logger.error(f"Verification flow error: {e}")
            return False

    async def _try_alternative_submit(self, page, form_detector, behavior, identity) -> bool:
        """Try alternative submission strategies when initial submit fails."""
        try:
            # Strategy 1: Try pressing Enter in the last field
            last_field = None
            for field_name in ["password", "email", "phone", "username", "full_name"]:
                sel = form_detector.detected_fields.get(field_name)
                if sel:
                    last_field = sel

            if last_field:
                element = await page.query_selector(last_field)
                if element:
                    await element.press("Enter")
                    await asyncio.sleep(3)

                    # Check if success
                    url = page.url
                    content_lower = (await page.content()).lower()
                    if any(kw in url.lower() for kw in ["dashboard", "welcome", "account", "home", "profile"]):
                        return True
                    if any(kw in content_lower for kw in ["welcome", "success", "account created", "dashboard"]):
                        return True

            # Strategy 2: Try JavaScript form submit
            try:
                await page.evaluate("""
                    () => {
                        const forms = document.forms;
                        if (forms.length > 0) {
                            forms[0].submit();
                        }
                    }
                """)
                await asyncio.sleep(3)
                url = page.url
                if url != form_detector.page.url:
                    content_lower = (await page.content()).lower()
                    if any(kw in content_lower for kw in ["welcome", "success", "account created"]):
                        return True
            except Exception:
                pass

            return False
        except Exception as e:
            logger.warning(f"Alternative submit failed: {e}")
            return False

    async def _test_password_policy(self, page, form_detector, validations) -> SecurityTestResult:
        """Test password policy enforcement (secondary analysis)."""
        pw_field = form_detector.detected_fields.get("password")
        if not pw_field:
            return SecurityTestResult(
                test_name="Password Policy Enforcement",
                passed=False,
                details={"status": "Password field not detected"}
            )

        pw_validation = validations.get("password", {})
        has_min_length = pw_validation.get("minLength", 0) > 0
        has_pattern = bool(pw_validation.get("pattern"))
        is_required = pw_validation.get("required", False)

        checks_passed = sum([is_required, has_min_length, has_pattern])
        passed = checks_passed >= 2

        return SecurityTestResult(
            test_name="Password Policy Enforcement",
            passed=passed,
            details={
                "status": "Password policy appears to be enforced" if passed else "Password policy may be weak",
                "html5_validations": {
                    "required": is_required,
                    "min_length": pw_validation.get("minLength"),
                    "pattern": pw_validation.get("pattern"),
                },
                "score": f"{checks_passed}/3 checks passed",
            }
        )

    async def _test_email_verification(self, page, attempt: SignupAttempt) -> SecurityTestResult:
        """Test if email verification is required (secondary analysis)."""
        content = await page.content()
        url = page.url.lower()
        title = await page.title()
        content_lower = content.lower()

        indicators = []
        verification_keywords = [
            "verify", "verification", "confirm", "confirmation",
            "email sent", "check your email", "activation",
            "activate", "link sent", "verify your email",
        ]

        for keyword in verification_keywords:
            if keyword in content_lower:
                indicators.append(f"Found keyword: '{keyword}'")

        if any(kw in url for kw in ["verify", "confirm", "activation", "pending"]):
            indicators.append("Redirected to verification page")

        passed = len(indicators) > 0

        return SecurityTestResult(
            test_name="Email Verification Requirement",
            passed=passed,
            details={
                "indicators_found": indicators,
                "status": "Email verification appears required" if passed else "No clear evidence of email verification",
            }
        )

    async def _test_duplicate_detection(self, page, attempt: SignupAttempt) -> SecurityTestResult:
        """Test if duplicate account detection is working (secondary analysis)."""
        content = await page.content()
        content_lower = content.lower()

        indicators = []
        duplicate_keywords = [
            "already exists", "already taken", "already registered",
            "duplicate", "account exists", "user exists",
            "email exists", "phone exists", "taken",
            "in use", "registered already", "try logging in",
        ]

        for keyword in duplicate_keywords:
            if keyword in content_lower:
                indicators.append(f"Found: '{keyword}'")

        passed = len(indicators) > 0

        return SecurityTestResult(
            test_name="Duplicate Account Detection",
            passed=passed,
            details={
                "indicators_found": indicators,
                "status": "Duplicate detection appears to be working" if passed else "No duplicate warning detected",
            }
        )

    def _analyze_rate_limit(self, current: SignupAttempt, previous: SignupAttempt) -> SecurityTestResult:
        """Analyze if rate limiting is working (secondary analysis)."""
        time_diff = self._time_diff_seconds(current.timestamp, previous.timestamp)
        was_blocked = not current.success
        rapid_signup = time_diff < 2.0

        passed = was_blocked and rapid_signup

        return SecurityTestResult(
            test_name="Rate Limiting Detection",
            passed=passed,
            details={
                "time_between_signups_seconds": round(time_diff, 2),
                "signup_blocked": was_blocked,
                "rapid_signup": rapid_signup,
                "status": "Rate limiting may be active" if passed else "Insufficient data to confirm rate limiting",
            }
        )

    async def _analyze_response(self, page, attempt: SignupAttempt, form_detector) -> tuple:
        """Analyze the page response after form submission."""
        content = await page.content()
        url = page.url.lower()
        title = await page.title()
        content_lower = content.lower()

        # If no fields were filled, cannot be a successful signup
        if not attempt.fields_filled or len(attempt.fields_filled) == 0:
            return False, "No form fields were filled — signup not attempted"

        # Success indicators
        success_indicators = [
            "welcome", "success", "account created", "registration complete",
            "signed up", "joined", "dashboard", "profile", "home",
            "thank you", "completed", "verified", "activated",
            "check your email", "verification sent", "confirm your email",
            "congratulations", "you're in", "get started",
        ]

        # Block/error indicators
        error_indicators = [
            "error", "invalid", "failed", "blocked", "denied",
            "unauthorized", "forbidden", "too many", "rate limit",
            "captcha", "robot", "bot detected", "automation",
            "already exists", "try again", "incorrect",
            "please correct", "field is required",
            "not available", "already taken", "not valid",
        ]

        original_domain = self._get_domain(self.target_url)
        current_domain = self._get_domain(url)

        success_score = 0
        error_score = 0

        for indicator in success_indicators:
            if indicator in content_lower:
                success_score += 1

        for indicator in error_indicators:
            if indicator in content_lower:
                error_score += 1

        # URL change to a different page is a strong success signal
        if current_domain != original_domain or url != self.target_url.lower():
            success_score += 2

        # Dashboard/profile/home in URL is very strong success
        if any(kw in url for kw in ["dashboard", "profile", "home", "account", "welcome"]):
            success_score += 5

        # Check for form still being present (means submission didn't go through)
        if form_detector.submit_button:
            try:
                still_has_submit = await page.query_selector(form_detector.submit_button)
                if still_has_submit:
                    error_score += 2
            except Exception:
                pass

        if success_score >= 3:
            return True, f"Signup appears successful (indicators: {success_score})"
        elif success_score > error_score and success_score >= 1:
            return True, f"Signup likely successful (success: {success_score}, errors: {error_score})"
        elif error_score >= 2:
            return False, f"Signup blocked or errors detected (errors: {error_score})"
        else:
            # Only treat as success if we actually got a different page
            if current_domain != original_domain:
                return True, "Redirected away from form — assuming success"
            return False, f"Ambiguous result (success: {success_score}, errors: {error_score}) — treating as blocked"

    def _get_domain(self, url: str) -> str:
        """Extract domain from URL."""
        try:
            from urllib.parse import urlparse
            return urlparse(url).netloc
        except Exception:
            return url

    def _time_diff_seconds(self, timestamp1: str, timestamp2: str) -> float:
        """Calculate time difference between two ISO timestamps."""
        try:
            t1 = datetime.fromisoformat(timestamp1)
            t2 = datetime.fromisoformat(timestamp2)
            return abs((t1 - t2).total_seconds())
        except Exception:
            return 0.0

    def _compile_results(self) -> Dict:
        """Compile all results into a comprehensive report."""
        duration = (self.end_time - self.start_time).total_seconds() if self.end_time and self.start_time else 0

        # Aggregate security test results
        all_security_results = []
        for attempt in self.attempts:
            all_security_results.extend(attempt.security_results)

        # Group by test name
        test_summary = {}
        for result in all_security_results:
            if result.test_name not in test_summary:
                test_summary[result.test_name] = {"passed": 0, "failed": 0, "total": 0}
            test_summary[result.test_name]["total"] += 1
            if result.passed:
                test_summary[result.test_name]["passed"] += 1
            else:
                test_summary[result.test_name]["failed"] += 1

        # Overall security score
        total_tests = len(all_security_results)
        passed_tests = sum(1 for r in all_security_results if r.passed)
        security_score = (passed_tests / total_tests * 100) if total_tests > 0 else 0

        successful_signups = len(self.created_accounts)
        attempted_count = len(self.attempts)
        blocked_signups = attempted_count - successful_signups

        # Track captcha and email stats
        captcha_solved_count = sum(1 for a in self.attempts if a.captcha_solved)
        email_verified_count = sum(1 for a in self.attempts if a.email_verified)

        return {
            "test_metadata": {
                "target_url": self.target_url,
                "num_accounts_requested": self.num_accounts,
                "num_accounts_executed": attempted_count,
                "start_time": self.start_time.isoformat() if self.start_time else None,
                "end_time": self.end_time.isoformat() if self.end_time else None,
                "duration_seconds": round(duration, 2),
                "captcha_solving": {
                    "enabled": bool(self.captcha_api_key),
                    "service": self.captcha_service if self.captcha_api_key else None,
                    "solved_count": captcha_solved_count,
                },
                "tests_configured": {
                    "captcha": self.test_captcha,
                    "rate_limiting": self.test_rate_limit,
                    "email_verification": self.test_email_verify,
                    "device_fingerprint": self.test_fingerprint,
                    "password_policy": self.test_password_policy,
                    "duplicate_detection": self.test_duplicate,
                },
            },
            "signup_summary": {
                "total_attempts": attempted_count,
                "successful": successful_signups,
                "blocked": blocked_signups,
                "success_rate": round(successful_signups / attempted_count * 100, 1) if attempted_count else 0,
                "captcha_solved": captcha_solved_count,
                "emails_verified": email_verified_count,
            },
            "security_score": {
                "overall_percentage": round(security_score, 1),
                "tests_passed": passed_tests,
                "tests_failed": total_tests - passed_tests,
                "total_tests": total_tests,
            },
            "test_breakdown": test_summary,
            "attempts": [a.to_dict() for a in self.attempts],
            "created_accounts": self.created_accounts,
            "recommendations": self._generate_recommendations(test_summary, successful_signups),
        }

    def _generate_recommendations(self, test_summary: Dict, successful_signups: int) -> List[str]:
        """Generate recommendations based on results."""
        recommendations = []

        for test_name, results in test_summary.items():
            if results["failed"] > results["passed"]:
                if test_name == "CAPTCHA Detection":
                    recommendations.append("HIGH: Add CAPTCHA (reCAPTCHA v2/v3 or hCaptcha) to prevent automated signups")
                elif test_name == "Rate Limiting Detection":
                    recommendations.append("HIGH: Implement rate limiting (max 5 signups per IP per hour)")
                elif test_name == "Email Verification Requirement":
                    recommendations.append("MEDIUM: Require email verification before account activation")
                elif test_name == "Password Policy Enforcement":
                    recommendations.append("MEDIUM: Enforce strong password policy (min 12 chars, mixed case, numbers, symbols)")
                elif test_name == "Duplicate Account Detection":
                    recommendations.append("MEDIUM: Check for duplicate email/phone before allowing registration")
                elif test_name == "Device Fingerprint Detection":
                    recommendations.append("LOW: Consider adding bot detection (FingerprintJS, DataDome)")

        if successful_signups > self.num_accounts * 0.5:
            recommendations.append("CRITICAL: Most signups succeeded — your signup page may be vulnerable to automation")

        if not recommendations:
            recommendations.append("Good: Most security features appear to be working correctly")

        return recommendations
