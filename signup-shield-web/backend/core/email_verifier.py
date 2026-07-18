# =============================================================================
# EMAIL VERIFIER MODULE
# Auto-creates temp emails, checks inbox, clicks verification links
# Supports: mail.tm, mail.gw (free temp mail APIs)
# =============================================================================

import asyncio
import json
import logging
import random
import re
import time
from datetime import datetime
from typing import Dict, List, Optional
from urllib.parse import urljoin

import aiohttp

logger = logging.getLogger(__name__)


class TempMailService:
    """Base class for temp mail services."""

    async def create_email(self) -> Dict:
        raise NotImplementedError

    async def check_inbox(self, token: str) -> List[Dict]:
        raise NotImplementedError

    async def get_message(self, token: str, message_id: str) -> Dict:
        raise NotImplementedError

    async def delete_email(self, token: str) -> bool:
        raise NotImplementedError


class MailTMService(TempMailService):
    """mail.tm - Free temporary email service API."""

    BASE_URL = "https://api.mail.tm"

    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                headers={"Content-Type": "application/json"},
                timeout=aiohttp.ClientTimeout(total=30)
            )
        return self.session

    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()

    async def _request(self, method: str, endpoint: str, token: str = None, data: Dict = None) -> Dict:
        """Make an API request to mail.tm."""
        session = await self._get_session()
        url = f"{self.BASE_URL}{endpoint}"

        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"

        try:
            async with session.request(method, url, headers=headers, json=data) as resp:
                if resp.status in (200, 201, 204):
                    if resp.status == 204:
                        return {"success": True}
                    return await resp.json()
                else:
                    text = await resp.text()
                    logger.warning(f"mail.tm API error {resp.status}: {text}")
                    return {"error": f"HTTP {resp.status}: {text}"}
        except Exception as e:
            logger.error(f"mail.tm request failed: {e}")
            return {"error": str(e)}

    async def get_domains(self) -> List[str]:
        """Get available email domains."""
        result = await self._request("GET", "/domains")
        if "error" in result:
            # Fallback domains
            return ["mail.tm", "trialos.dev", "habibur.dev", "spamok.dev"]
        domains = result.get("hydra:member", [])
        return [d["domain"] for d in domains if d.get("isActive", True)]

    async def create_email(self) -> Dict:
        """Create a new temporary email address with random domain rotation."""
        # Get available domains
        domains = await self.get_domains()
        if not domains:
            return {"error": "No available domains"}

        # Shuffle and try multiple domains to avoid domain-based blocking
        random.shuffle(domains)
        last_error = None

        for domain in domains[:5]:  # Try up to 5 different domains
            uid = str(random.randint(100000, 999999))
            username = f"u{uid}_{int(time.time() * 1000) % 100000}"
            email = f"{username}@{domain}"
            password = f"Shield{random.randint(1000, 9999)}!"

            # Create account
            result = await self._request("POST", "/accounts", data={
                "address": email,
                "password": password
            })

            if "id" in result:
                # Successfully created — get auth token
                token_result = await self._request("POST", "/token", data={
                    "address": email,
                    "password": password
                })

                if "token" in token_result:
                    return {
                        "email": email,
                        "password": password,
                        "token": token_result["token"],
                        "id": token_result.get("id", result.get("id", "")),
                        "service": "mail.tm"
                    }

            last_error = result.get("detail", result.get("error", "Unknown error"))
            await asyncio.sleep(0.5)

        # Fallback: try first domain with completely random name
        domain = domains[0]
        uid = str(random.randint(100000, 9999999))
        email = f"u{uid}_{int(time.time() * 100000)}@{domain}"
        password = f"Shield{random.randint(1000, 9999)}!"
        result = await self._request("POST", "/accounts", data={
            "address": email,
            "password": password
        })
        token_result = await self._request("POST", "/token", data={
            "address": email,
            "password": password
        })
        if "token" in token_result:
            return {
                "email": email,
                "password": password,
                "token": token_result["token"],
                "id": token_result.get("id", result.get("id", "")),
                "service": "mail.tm"
            }

        return {"error": f"Failed to create temp email: {last_error}"}

    async def check_inbox(self, token: str) -> List[Dict]:
        """Check inbox for new messages."""
        result = await self._request("GET", "/messages", token=token)
        if "hydra:member" in result:
            return result["hydra:member"]
        return []

    async def get_message(self, token: str, message_id: str) -> Dict:
        """Get full message content."""
        return await self._request("GET", f"/messages/{message_id}", token=token)

    async def delete_email(self, token: str) -> bool:
        """Delete the email account."""
        result = await self._request("DELETE", "/me", token=token)
        return "error" not in result

    async def get_account_info(self, token: str) -> Dict:
        """Get account info."""
        return await self._request("GET", "/me", token=token)


class EmailVerifier:
    """
    Email verification handler.
    Creates temp email, monitors inbox, extracts verification links.
    """

    VERIFICATION_KEYWORDS = [
        "verify", "verification", "confirm", "confirmation",
        "activate", "activation", "validate", "validation",
        "welcome", "email verification", "verify email",
        "confirm email", "account activation",
    ]

    def __init__(self, mail_service: TempMailService = None):
        self.mail_service = mail_service or MailTMService()
        self.verified_accounts: List[Dict] = []

    async def create_verified_email(self) -> Dict:
        """Create a temp email ready for verification."""
        result = await self.mail_service.create_email()
        if "error" in result:
            logger.error(f"Failed to create temp email: {result['error']}")
            return result

        logger.info(f"Created temp email: {result['email']}")
        return result

    async def wait_for_verification_email(
        self,
        token: str,
        timeout: int = 120,
        poll_interval: int = 5
    ) -> Optional[Dict]:
        """
        Poll inbox and wait for verification email.

        Args:
            token: Mail service auth token
            timeout: Maximum wait time in seconds
            poll_interval: Seconds between inbox checks

        Returns:
            Message dict if found, None if timeout
        """
        logger.info(f"Waiting for verification email (timeout: {timeout}s)...")
        start_time = time.time()

        seen_message_ids = set()

        while time.time() - start_time < timeout:
            messages = await self.mail_service.check_inbox(token)

            for msg in messages:
                msg_id = msg.get("id")
                if msg_id in seen_message_ids:
                    continue
                seen_message_ids.add(msg_id)

                subject = (msg.get("subject") or "").lower()
                from_addr = (msg.get("from", {}) or {}).get("address", "").lower()

                # Check if it's a verification email
                is_verification = any(kw in subject for kw in self.VERIFICATION_KEYWORDS)

                if is_verification:
                    logger.info(f"Found verification email: '{msg.get('subject')}' from {from_addr}")

                    # Get full message content
                    full_msg = await self.mail_service.get_message(token, msg_id)

                    return {
                        "id": msg_id,
                        "subject": msg.get("subject"),
                        "from": from_addr,
                        "intro": msg.get("intro", ""),
                        "text": full_msg.get("text", ""),
                        "html": full_msg.get("html", ""),
                        "created_at": msg.get("createdAt"),
                    }

            await asyncio.sleep(poll_interval)

        logger.warning("Timeout waiting for verification email")
        return None

    def extract_verification_link(self, message: Dict) -> Optional[str]:
        """
        Extract verification/confirmation link from email content.

        Args:
            message: Email message dict with text and html

        Returns:
            URL string if found, None otherwise
        """
        content = message.get("html", "") or message.get("text", "")

        if not content:
            return None

        # Pattern 1: Explicit verification URLs
        patterns = [
            # Generic verification URLs
            r'href=["\'](https?://[^"\']*?(?:verify|confirm|activate|validate|auth)[^"\']*?)["\']',
            r'(https?://[^\s<>"\']*?(?:verify|confirm|activate|validate|auth)[^\s<>"\']*?)',
            # Token-based links
            r'href=["\'](https?://[^"\']*?(?:token|code|key)=[^"\']*?)["\']',
            r'(https?://[^\s<>"\']*?(?:token|code|key)=[^\s<>"\']*?)',
            # Shortened links that look like verification
            r'href=["\'](https?://[^"\']*?/v/[^"\']*?)["\']',
            # Any button/link in email
            r'<a[^>]*href=["\'](https?://[^"\']+)["\'][^>]*>(?:verify|confirm|activate|click|here|verify email|confirm email)</a>',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                # Return the first valid URL
                for match in matches:
                    url = match if match.startswith("http") else None
                    if url:
                        # Clean the URL
                        url = url.replace("&amp;", "&")
                        logger.info(f"Extracted verification link: {url[:80]}...")
                        return url

        # Fallback: Find any HTTP link in the email
        all_links = re.findall(r'href=["\'](https?://[^"\']+)["\']', content)
        if all_links:
            # Filter out unsubscribe, preferences, etc.
            for link in all_links:
                skip_keywords = ["unsubscribe", "preferences", "privacy", "help", "support", "login"]
                if not any(kw in link.lower() for kw in skip_keywords):
                    logger.info(f"Using fallback link: {link[:80]}...")
                    return link.replace("&amp;", "&")

        logger.warning("No verification link found in email")
        return None

    async def verify_email(
        self,
        token: str,
        page=None,
        timeout: int = 120
    ) -> Dict:
        """
        Full verification flow: wait for email, extract link, optionally click.

        Args:
            token: Mail service auth token
            page: Optional Playwright page to click the link
            timeout: Max wait time

        Returns:
            Verification result dict
        """
        result = {
            "email_verified": False,
            "verification_email_received": False,
            "link_extracted": False,
            "link_clicked": False,
            "verification_url": None,
            "error": None,
            "email_subject": None,
            "time_taken_seconds": 0,
        }

        start_time = time.time()

        try:
            # Wait for verification email
            message = await self.wait_for_verification_email(token, timeout=timeout)

            if not message:
                result["error"] = "No verification email received within timeout"
                result["time_taken_seconds"] = round(time.time() - start_time, 2)
                return result

            result["verification_email_received"] = True
            result["email_subject"] = message.get("subject")

            # Extract verification link
            link = self.extract_verification_link(message)

            if link:
                result["link_extracted"] = True
                result["verification_url"] = link

                # Click the link if browser page is provided
                if page:
                    try:
                        logger.info(f"Clicking verification link: {link[:60]}...")
                        await page.goto(link, wait_until="domcontentloaded", timeout=60000)
                        await asyncio.sleep(3)
                        result["link_clicked"] = True

                        # Check if verification was successful
                        page_content = (await page.content()).lower()
                        success_indicators = [
                            "verified", "confirmed", "activated", "success",
                            "thank you", "welcome", "email verified",
                            "account activated", "verification complete",
                        ]

                        if any(ind in page_content for ind in success_indicators):
                            result["email_verified"] = True
                            logger.info("Email verified successfully!")
                        else:
                            result["error"] = "Link clicked but verification status unclear"

                    except Exception as e:
                        result["error"] = f"Failed to click verification link: {e}"
                else:
                    # No page provided - just return the link for manual verification
                    result["error"] = "Verification link extracted but no browser page to click"

            else:
                result["error"] = "Could not extract verification link from email"

        except Exception as e:
            result["error"] = f"Verification failed: {e}"
            logger.error(f"Email verification error: {e}")

        finally:
            result["time_taken_seconds"] = round(time.time() - start_time, 2)

        return result

    async def close(self):
        """Close mail service connections."""
        await self.mail_service.close()

    def add_verified_account(self, email: str, password: str, identity: Dict = None, verified: bool = True):
        """Add a successfully verified account to the list."""
        account = {
            "email": email,
            "password": password,
            "verified": verified,
            "timestamp": datetime.now().isoformat(),
            "identity": identity,
        }
        self.verified_accounts.append(account)
        logger.info(f"Added verified account: {email}")

    def get_verified_accounts(self) -> List[Dict]:
        """Get list of all verified accounts."""
        return self.verified_accounts

    def get_summary(self) -> Dict:
        """Get summary of verification results."""
        total = len(self.verified_accounts)
        verified = sum(1 for a in self.verified_accounts if a["verified"])
        return {
            "total_accounts": total,
            "verified": verified,
            "failed": total - verified,
            "accounts": self.verified_accounts,
        }
