# =============================================================================
# BROWSER AUTOMATION WITH STEALTH
# Manages browser lifecycle with anti-detection patches
# =============================================================================

import asyncio
import logging
import random
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class BrowserManager:
    """Manages browser automation with stealth patches."""

    def __init__(self, headless: bool = True, proxy: Optional[str] = None):
        self.headless = headless
        self.proxy = proxy
        self.browser = None
        self.context = None
        self.page = None

    async def launch(self, fingerprint: Dict):
        """Launch browser with stealth configuration."""
        try:
            from playwright.async_api import async_playwright

            self.playwright = await async_playwright().start()

            # Build launch args from fingerprint
            args = self._build_launch_args(fingerprint)

            logger.info("Launching browser...")
            self.browser = await self.playwright.chromium.launch(
                headless=self.headless,
                args=args,
            )

            # Create context with fingerprint
            context_options = self._build_context_options(fingerprint)
            self.context = await self.browser.new_context(**context_options)

            # Add stealth scripts
            await self._apply_stealth_scripts(fingerprint)

            # Create page
            self.page = await self.context.new_page()

            # Apply additional page-level patches
            await self._apply_page_patches(fingerprint)

            logger.info("Browser launched successfully")
            return True

        except ImportError:
            logger.error("playwright not installed. Install with: pip install playwright && python -m playwright install chromium")
            return False
        except Exception as e:
            logger.error(f"Failed to launch browser: {e}")
            return False

    def _build_launch_args(self, fingerprint: Dict) -> list:
        """Build Chrome launch arguments from fingerprint."""
        screen = fingerprint["screen"]
        browser = fingerprint["browser"]

        args = [
            "--disable-blink-features=AutomationControlled",
            "--disable-features=IsolateOrigins,site-per-process",
            "--disable-site-isolation-trials",
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage",
            "--disable-accelerated-2d-canvas",
            "--disable-gpu",
            "--hide-scrollbars",
            "--disable-notifications",
            "--disable-extensions",
            "--disable-default-apps",
            "--mute-audio",
            "--no-first-run",
            "--no-default-browser-check",
            f"--lang={browser['language']},en",
            f"--window-size={screen['width']},{screen['height']}",
            f"--force-device-scale-factor={screen['pixel_ratio']}",
            f"--user-agent={browser['user_agent']}",
        ]

        if self.proxy:
            args.append(f"--proxy-server={self.proxy}")

        return args

    def _build_context_options(self, fingerprint: Dict) -> Dict:
        """Build browser context options from fingerprint."""
        screen = fingerprint["screen"]
        browser = fingerprint["browser"]
        tz = fingerprint["timezone"]

        return {
            "viewport": {
                "width": screen["width"],
                "height": screen["height"],
            },
            "user_agent": browser["user_agent"],
            "locale": browser["language"],
            "timezone_id": tz["timezone"],
            "permissions": ["geolocation"],
            "color_scheme": "light",
            "reduced_motion": "no-preference",
            "device_scale_factor": screen["pixel_ratio"],
            "is_mobile": False,
            "has_touch": browser["touch_support"],
            "java_script_enabled": True,
        }

    async def _apply_stealth_scripts(self, fingerprint: Dict):
        """Apply CDP-level stealth patches."""
        screen = fingerprint["screen"]
        browser = fingerprint["browser"]
        webgl = fingerprint["webgl"]
        tz = fingerprint["timezone"]

        # Override navigator.webdriver
        await self.context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });
        """)

        # Remove chrome automation markers
        await self.context.add_init_script("""
            delete navigator.__proto__.webdriver;

            // Remove CDC markers
            const props = Object.getOwnPropertyNames(window);
            for (const prop of props) {
                if (prop.includes('cdc_') || prop.includes('cdc_a')) {
                    delete window[prop];
                }
            }
        """)

        # Override navigator.plugins
        await self.context.add_init_script("""
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5],
            });
        """)

        # Override navigator.languages
        await self.context.add_init_script(f"""
            Object.defineProperty(navigator, 'languages', {{
                get: () => ['{browser['language']}', 'en'],
            }});
        """)

        # Override screen properties
        await self.context.add_init_script(f"""
            Object.defineProperty(screen, 'width', {{ get: () => {screen['width']} }});
            Object.defineProperty(screen, 'height', {{ get: () => {screen['height']} }});
            Object.defineProperty(screen, 'availWidth', {{ get: () => {screen['avail_width']} }});
            Object.defineProperty(screen, 'availHeight', {{ get: () => {screen['avail_height']} }});
            Object.defineProperty(screen, 'colorDepth', {{ get: () => {screen['color_depth']} }});
            Object.defineProperty(screen, 'pixelDepth', {{ get: () => {screen['color_depth']} }});
        """)

        # Override hardware properties
        await self.context.add_init_script(f"""
            Object.defineProperty(navigator, 'hardwareConcurrency', {{
                get: () => {browser['hardware_concurrency']},
            }});
            Object.defineProperty(navigator, 'deviceMemory', {{
                get: () => {browser['device_memory']},
            }});
        """)

        # Override WebGL fingerprint
        await self.context.add_init_script(f"""
            const getParameter = WebGLRenderingContext.prototype.getParameter;
            WebGLRenderingContext.prototype.getParameter = function(parameter) {{
                if (parameter === 37445) {{
                    return '{webgl['vendor']}';
                }}
                if (parameter === 37446) {{
                    return '{webgl['renderer']}';
                }}
                return getParameter(parameter);
            }};
        """)

        # Canvas noise injection
        await self.context.add_init_script("""
            const originalGetImageData = CanvasRenderingContext2D.prototype.getImageData;
            CanvasRenderingContext2D.prototype.getImageData = function(x, y, w, h) {
                const imageData = originalGetImageData.call(this, x, y, w, h);
                const data = imageData.data;
                for (let i = 0; i < data.length; i += 4) {
                    data[i] += (Math.random() < 0.5 ? -1 : 1);
                    data[i + 1] += (Math.random() < 0.5 ? -1 : 1);
                    data[i + 2] += (Math.random() < 0.5 ? -1 : 1);
                }
                return imageData;
            };
        """)

        # AudioContext timing variation
        await self.context.add_init_script("""
            if (typeof AudioBuffer !== 'undefined' && AudioBuffer.prototype.copyFromChannel) {
                const originalCopy = AudioBuffer.prototype.copyFromChannel;
                AudioBuffer.prototype.copyFromChannel = function(destination, channelNumber, startInChannel) {
                    const result = originalCopy.call(this, destination, channelNumber, startInChannel);
                    for (let i = 0; i < destination.length; i++) {
                        destination[i] += (Math.random() - 0.5) * 0.0001;
                    }
                    return result;
                };
            }
        """)

        # Mock chrome.runtime and chrome.app
        await self.context.add_init_script("""
            if (typeof chrome !== 'undefined') {
                if (!chrome.runtime) {
                    chrome.runtime = {};
                }
                if (!chrome.app) {
                    chrome.app = {
                        isInstalled: false,
                        InstallState: { DISABLED: "disabled", INSTALLED: "installed", NOT_INSTALLED: "not_installed" },
                        RunningState: { CANNOT_RUN: "cannot_run", READY_TO_RUN: "ready_to_run", RUNNING: "running" }
                    };
                }
            }
        """)

    async def _apply_page_patches(self, fingerprint: Dict):
        """Apply page-level patches."""
        # Set geolocation if available
        if fingerprint.get("geolocation"):
            await self.context.set_geolocation(fingerprint["geolocation"])

    async def navigate(self, url: str, wait_until: str = "domcontentloaded"):
        """Navigate to a URL with retry logic for resilience."""
        if not self.page:
            logger.error("Browser not launched")
            return False

        # Retry configuration (different wait strategies + increasing timeouts)
        strategies = [
            {"wait_until": "domcontentloaded", "timeout": 60000, "label": "fast"},
            {"wait_until": "load", "timeout": 90000, "label": "normal"},
            {"wait_until": "networkidle", "timeout": 120000, "label": "full"},
        ]

        # Start from the strategy that matches the requested wait_until
        start_idx = 0
        for i, s in enumerate(strategies):
            if s["wait_until"] == wait_until:
                start_idx = i
                break

        last_error = None
        for attempt_idx in range(start_idx, len(strategies)):
            strategy = strategies[attempt_idx]
            try:
                logger.info(
                    f"Navigation attempt {attempt_idx + 1}/{len(strategies) - start_idx} "
                    f"to: {url} (wait={strategy['label']}, timeout={strategy['timeout']}ms)"
                )

                # Navigate with current strategy
                response = await self.page.goto(
                    url,
                    wait_until=strategy["wait_until"],
                    timeout=strategy["timeout"]
                )

                # Wait for page to be interactive after navigation
                try:
                    await self.page.wait_for_load_state("domcontentloaded", timeout=10000)
                except Exception:
                    pass  # Non-critical, continue

                if response:
                    status = response.status
                    logger.info(f"  Navigation success, status: {status}")
                    # Treat 4xx/5xx as navigated but return False
                    return status < 400 if status >= 400 else True

                # No response but no exception — page loaded (e.g. cached)
                logger.info("  Navigation succeeded (no response object)")
                return True

            except Exception as e:
                last_error = e
                logger.warning(f"  Navigation attempt {attempt_idx + 1} failed: {e}")

                # Brief pause before retry
                if attempt_idx < len(strategies) - 1:
                    await asyncio.sleep(2)

        logger.error(f"All navigation strategies failed for {url}: {last_error}")
        return False

    async def take_screenshot(self, path: str):
        """Take a screenshot of the current page."""
        if self.page:
            await self.page.screenshot(path=path, full_page=True)
            logger.info(f"Screenshot saved: {path}")

    async def get_page_content(self) -> str:
        """Get the current page HTML content."""
        if self.page:
            return await self.page.content()
        return ""

    async def close(self):
        """Close the browser."""
        try:
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if hasattr(self, 'playwright'):
                await self.playwright.stop()
            logger.info("Browser closed")
        except Exception as e:
            logger.error(f"Error closing browser: {e}")

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
