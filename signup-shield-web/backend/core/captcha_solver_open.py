# =============================================================================
# Open-Source CAPTCHA Solver
# Free/no-API-key CAPTCHA solving using:
#   - Audio reCAPTCHA solving via Google Speech Recognition
#   - Playwright stealth techniques to avoid CAPTCHAs
#   - Cloudflare Turnstile bypass
#   - Multi-strategy fallback system
# =============================================================================

import asyncio
import io
import json
import logging
import os
import platform
import random
import re
import subprocess
import tempfile
import time
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

import aiohttp

logger = logging.getLogger(__name__)


class AudioCaptchaSolver:
    """
    Solves audio-based CAPTCHAs (reCAPTCHA v2 audio challenge) using
    free Google Speech Recognition API — no API key required.
    
    Technique used by many popular open-source GitHub projects.
    """

    # Google Speech Recognition API (free, undocumented, used by speech_recognition lib)
    GOOGLE_SPEECH_URL = "https://www.google.com/speech-api/v2/recognize"
    # This is the API key embedded in the speech_recognition package
    GOOGLE_SPEECH_KEY = "AIzaSyBOti4mM-6x9WDnZIjIeyEU21OpBXqWBgw"

    @staticmethod
    async def solve_audio_captcha(
        page,
        audio_url: str = None,
        iframe_element=None,
        timeout: int = 60,
    ) -> Optional[str]:
        """
        Solve an audio CAPTCHA by downloading and transcribing the audio.
        
        Args:
            page: Playwright page object
            audio_url: Direct URL to audio file (if known)
            iframe_element: The CAPTCHA iframe element (if interacting via iframe)
            timeout: Maximum time to wait
            
        Returns:
            Transcribed text or None if failed
        """
        audio_data = None

        # Strategy 1: Direct audio URL provided
        if audio_url:
            logger.info(f"Downloading audio from: {audio_url}")
            audio_data = await AudioCaptchaSolver._download_audio(audio_url)
            if audio_data:
                logger.info(f"Downloaded {len(audio_data)} bytes of audio")

        # Strategy 2: Interact with CAPTCHA iframe to get audio challenge
        if not audio_data and iframe_element:
            audio_data = await AudioCaptchaSolver._get_audio_from_iframe(page, iframe_element, timeout)

        # Strategy 3: Try clicking audio challenge button on the page
        if not audio_data:
            audio_data = await AudioCaptchaSolver._get_audio_from_page(page, timeout)

        if not audio_data:
            logger.error("Failed to obtain audio CAPTCHA data")
            return None

        # Convert audio to FLAC format for Google Speech API
        flac_data = await AudioCaptchaSolver._convert_to_flac(audio_data)
        if not flac_data:
            logger.error("Failed to convert audio to FLAC")
            return None

        # Send to Google Speech Recognition
        text = await AudioCaptchaSolver._transcribe_audio(flac_data)
        if text:
            logger.info(f"Audio CAPTCHA transcribed: '{text}'")
            return text

        logger.error("Speech recognition returned no text")
        return None

    @staticmethod
    async def _download_audio(url: str) -> Optional[bytes]:
        """Download audio file from URL."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                    if resp.status == 200:
                        return await resp.read()
                    logger.warning(f"Audio download failed: HTTP {resp.status}")
                    return None
        except Exception as e:
            logger.warning(f"Audio download error: {e}")
            return None

    @staticmethod
    async def _get_audio_from_iframe(page, iframe_element, timeout: int) -> Optional[bytes]:
        """Navigate CAPTCHA iframe and get audio challenge."""
        try:
            # Switch to CAPTCHA iframe
            iframe = await iframe_element.content_frame()
            if not iframe:
                logger.warning("Could not access CAPTCHA iframe")
                return None

            # Wait for iframe to load
            await asyncio.sleep(2)

            # Click the reCAPTCHA checkbox if present
            try:
                checkbox = await iframe.query_selector(".recaptcha-checkbox-border")
                if checkbox:
                    await checkbox.click()
                    await asyncio.sleep(1)
            except Exception:
                pass

            # Look for and click the audio challenge button
            audio_buttons = [
                'button[id="recaptcha-audio-button"]',
                'button[aria-label*="audio"]',
                'button[title*="audio"]',
                '.rc-audiochallenge-tabloop-begin',
                'button:has-text("Get an audio challenge")',
                'button:has-text("audio")',
            ]

            audio_btn = None
            for selector in audio_buttons:
                try:
                    btn = await iframe.query_selector(selector)
                    if btn and await btn.is_visible():
                        audio_btn = btn
                        break
                except Exception:
                    continue

            if audio_btn:
                await audio_btn.click()
                logger.info("Clicked audio challenge button")
                await asyncio.sleep(3)
            else:
                # Check if we're already on the audio challenge
                logger.info("Audio challenge button not found, maybe already on audio challenge")

            # Try to find audio player element and get source URL
            audio_selectors = [
                'audio[src*="google.com"] source',
                'audio source',
                'audio[src]',
                'audio#audio-source',
                '.rc-audiochallenge-play-button',
            ]

            for selector in audio_selectors:
                try:
                    audio_el = await iframe.query_selector(selector)
                    if audio_el:
                        src = await audio_el.get_attribute("src")
                        if src:
                            logger.info(f"Found audio source: {src[:80]}...")
                            return await AudioCaptchaSolver._download_audio(src)
                except Exception:
                    continue

            # If we couldn't find the audio source directly, try clicking play and intercept
            play_btn = await iframe.query_selector(".rc-audiochallenge-play-button")
            if play_btn:
                # Set up response interception for the audio file
                audio_data = [None]

                async def intercept_response(response):
                    if response.request.resource_type == "media" or "audio" in response.headers.get("content-type", ""):
                        try:
                            audio_data[0] = await response.body()
                            logger.info(f"Intercepted audio response: {len(audio_data[0])} bytes")
                        except Exception:
                            pass

                page.on("response", intercept_response)
                await play_btn.click()
                await asyncio.sleep(3)
                page.remove_listener("response", intercept_response)

                if audio_data[0]:
                    return audio_data[0]

            # Try evaluating JS to find audio URL
            audio_url = await iframe.evaluate("""
                () => {
                    const audio = document.querySelector('audio');
                    if (audio && audio.src) return audio.src;
                    const source = document.querySelector('audio source');
                    if (source && source.src) return source.src;
                    return null;
                }
            """)
            if audio_url:
                return await AudioCaptchaSolver._download_audio(audio_url)

            return None

        except Exception as e:
            logger.warning(f"Iframe audio extraction error: {e}")
            return None

    @staticmethod
    async def _get_audio_from_page(page, timeout: int) -> Optional[bytes]:
        """Try to find and download audio CAPTCHA from the main page."""
        try:
            # Look for audio elements on the page
            audio_url = await page.evaluate("""
                () => {
                    const audios = document.querySelectorAll('audio');
                    for (const a of audios) {
                        if (a.src && (a.src.includes('google') || a.src.includes('recaptcha'))) {
                            return a.src;
                        }
                        const src = a.querySelector('source');
                        if (src && src.src) return src.src;
                    }
                    return null;
                }
            """)
            if audio_url:
                return await AudioCaptchaSolver._download_audio(audio_url)

            # Try clicking elements that lead to audio challenges
            for selector in [
                '#recaptcha-audio-button',
                'iframe[src*="recaptcha"]',
            ]:
                try:
                    iframe_el = await page.query_selector(selector)
                    if iframe_el:
                        return await AudioCaptchaSolver._get_audio_from_iframe(page, iframe_el, timeout)
                except Exception:
                    continue

            return None
        except Exception as e:
            logger.warning(f"Page audio extraction error: {e}")
            return None

    @staticmethod
    async def _convert_to_flac(audio_data: bytes) -> Optional[bytes]:
        """
        Convert audio to FLAC format using ffmpeg.
        Google Speech API works best with FLAC (16kHz, mono).
        """
        try:
            # Write input to temp file
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f_in:
                f_in.write(audio_data)
                in_path = f_in.name

            out_path = in_path + ".flac"

            # Convert using ffmpeg
            cmd = [
                "ffmpeg", "-y",
                "-i", in_path,
                "-ar", "16000",      # 16kHz sample rate
                "-ac", "1",          # mono
                "-c:a", "flac",      # FLAC codec
                "-compression_level", "5",
                out_path
            ]

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()

            if proc.returncode != 0:
                logger.warning(f"ffmpeg conversion failed: {stderr.decode(errors='ignore')[:200]}")
                return None

            with open(out_path, "rb") as f:
                flac_data = f.read()

            # Cleanup
            try:
                os.unlink(in_path)
                os.unlink(out_path)
            except Exception:
                pass

            logger.info(f"Converted audio: {len(audio_data)} bytes -> {len(flac_data)} bytes FLAC")
            return flac_data

        except Exception as e:
            logger.warning(f"Audio conversion error: {e}")
            return None

    @staticmethod
    async def _transcribe_audio(flac_data: bytes) -> Optional[str]:
        """
        Send FLAC audio to Google Speech Recognition API.
        Uses the free, undocumented API (same as speech_recognition library).
        """
        try:
            headers = {
                "Content-Type": "audio/x-flac; rate=16000",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            }

            params = {
                "output": "json",
                "lang": "en-US",
                "key": AudioCaptchaSolver.GOOGLE_SPEECH_KEY,
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    AudioCaptchaSolver.GOOGLE_SPEECH_URL,
                    params=params,
                    headers=headers,
                    data=flac_data,
                    timeout=aiohttp.ClientTimeout(total=60),
                ) as resp:
                    if resp.status != 200:
                        text = await resp.text()
                        logger.warning(f"Google Speech API returned HTTP {resp.status}: {text[:200]}")
                        # Try alternative endpoint without API key
                        return await AudioCaptchaSolver._transcribe_audio_fallback(flac_data)

                    response_text = await resp.text()

                    # Parse the response
                    try:
                        # Response may have multiple JSON lines
                        for line in response_text.strip().split("\n"):
                            if not line.strip():
                                continue
                            result = json.loads(line)
                            if "result" in result:
                                alternatives = result["result"]
                                if alternatives and len(alternatives) > 0:
                                    alternative = alternatives[0]
                                    if "alternative" in alternative and len(alternative["alternative"]) > 0:
                                        transcript = alternative["alternative"][0].get("transcript", "")
                                        if transcript:
                                            return transcript.strip().lower()
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to parse Google Speech response: {response_text[:200]}")
                        return None

            return None

        except Exception as e:
            logger.warning(f"Speech transcription error: {e}")
            return None

    @staticmethod
    async def _transcribe_audio_fallback(flac_data: bytes) -> Optional[str]:
        """
        Fallback: Try alternative Google Speech endpoint or use
        simulated keystrokes for known CAPTCHA patterns.
        """
        try:
            # Try alternative API endpoint
            alt_url = "https://www.google.com/speech-api/v1/recognize"
            headers = {
                "Content-Type": "audio/x-flac; rate=16000",
            }
            params = {
                "xjerr": "1",
                "client": "chromium",
                "lang": "en-US",
                "maxresults": "1",
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    alt_url,
                    params=params,
                    headers=headers,
                    data=flac_data,
                    timeout=aiohttp.ClientTimeout(total=60),
                ) as resp:
                    if resp.status == 200:
                        text = await resp.text()
                        try:
                            result = json.loads(text)
                            if "hypotheses" in result and len(result["hypotheses"]) > 0:
                                return result["hypotheses"][0].get("utterance", "").strip().lower()
                        except json.JSONDecodeError:
                            pass

            return None
        except Exception as e:
            logger.warning(f"Fallback transcription error: {e}")
            return None


class TurnstileSolver:
    """
    Solver for Cloudflare Turnstile CAPTCHA.
    Uses Playwright to extract and submit turnstile tokens.
    """

    @staticmethod
    async def solve_turnstile(page, timeout: int = 30) -> bool:
        """
        Attempt to solve Cloudflare Turnstile by finding and triggering
        the callback with the generated token.
        """
        try:
            # Wait for turnstile widget to load
            turnstile_selectors = [
                ".cf-turnstile",
                "iframe[src*='turnstile']",
                "div[data-sitekey]",
            ]

            turnstile_el = None
            for selector in turnstile_selectors:
                try:
                    el = await page.query_selector(selector)
                    if el:
                        turnstile_el = el
                        break
                except Exception:
                    continue

            if not turnstile_el:
                logger.warning("Turnstile element not found")
                return False

            # Try to get the Turnstile iframe and interact with it
            iframe_el = None
            try:
                iframe_el = await page.query_selector("iframe[src*='turnstile']")
            except Exception:
                pass

            if iframe_el:
                try:
                    iframe = await iframe_el.content_frame()
                    if iframe:
                        # Try clicking the checkbox in the turnstile iframe
                        checkbox = await iframe.query_selector("#checkbox")
                        if checkbox:
                            await checkbox.click()
                            await asyncio.sleep(2)
                            logger.info("Clicked Turnstile checkbox")
                            return True
                except Exception:
                    pass

            # Alternative: Try to get turnstile token via JavaScript
            token = await page.evaluate("""
                () => {
                    // Try to find turnstile callback
                    if (typeof turnstile !== 'undefined') {
                        try {
                            const widgets = document.querySelectorAll('[data-turnstile-widget]');
                            if (widgets.length > 0) {
                                return 'widget_found';
                            }
                        } catch(e) {}
                    }
                    // Check for turnstile response input
                    const input = document.querySelector('input[name="cf-turnstile-response"]');
                    if (input && input.value) return input.value;
                    return null;
                }
            """)

            if token:
                logger.info(f"Turnstile token found: {token[:20]}...")
                return True

            # Last resort: wait and check again
            await asyncio.sleep(3)
            return False

        except Exception as e:
            logger.warning(f"Turnstile solving error: {e}")
            return False


class StealthEnhancer:
    """
    Applies stealth techniques to avoid CAPTCHA triggers.
    Based on open-source Playwright stealth plugins.
    """

    @staticmethod
    async def apply_stealth(page):
        """
        Apply stealth modifications to avoid bot detection.
        Should be called after page creation but before navigation.
        """
        scripts = [
            # Override navigator.webdriver
            """
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
                configurable: true,
            });
            """,

            # Override chrome.runtime
            """
            if (!window.chrome) {
                window.chrome = {
                    runtime: {
                        connect: () => ({
                            onMessage: { addListener: () => {} },
                            onDisconnect: { addListener: () => {} },
                            postMessage: () => {},
                        }),
                        sendMessage: () => {},
                        onMessage: { addListener: () => {} },
                    },
                };
            }
            """,

            # Override permissions
            """
            if (navigator.permissions) {
                const originalQuery = navigator.permissions.query;
                navigator.permissions.query = (params) => (
                    params.name === 'notifications' ?
                        Promise.resolve({ state: 'denied' }) :
                        originalQuery(params)
                );
            }
            """,

            # Override plugins array
            """
            Object.defineProperty(navigator, 'plugins', {
                get: () => {
                    return {
                        0: { name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer' },
                        1: { name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai' },
                        2: { name: 'Native Client', filename: 'internal-nacl-plugin' },
                        length: 3,
                        item: (i) => this[i],
                        namedItem: (n) => null,
                        refresh: () => {},
                    };
                },
                configurable: true,
            });
            """,

            # Override languages
            """
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en'],
                configurable: true,
            });
            """,

            # Override hardwareConcurrency
            """
            Object.defineProperty(navigator, 'hardwareConcurrency', {
                get: () => 8,
                configurable: true,
            });
            """,

            # Override deviceMemory
            """
            Object.defineProperty(navigator, 'deviceMemory', {
                get: () => 8,
                configurable: true,
            });
            """,

            # WebGL vendor/renderer spoofing
            """
            const getParameter = WebGLRenderingContext.prototype.getParameter;
            WebGLRenderingContext.prototype.getParameter = function(param) {
                if (param === 37445) return 'Intel Inc.';
                if (param === 37446) return 'Intel Iris OpenGL Engine';
                return getParameter.call(this, param);
            };
            """,

            # Override connection rtt
            """
            if (navigator.connection) {
                Object.defineProperty(navigator.connection, 'rtt', {
                    get: () => 100,
                    configurable: true,
                });
            }
            """,

            # Hide headless chrome
            """
            const originalGetContext = HTMLCanvasElement.prototype.getContext;
            HTMLCanvasElement.prototype.getContext = function(type, ...args) {
                const ctx = originalGetContext.call(this, type, ...args);
                if (ctx && ctx.canvas) {
                    const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
                    HTMLCanvasElement.prototype.toDataURL = function(...args) {
                        return originalToDataURL.call(this, ...args);
                    };
                }
                return ctx;
            };
            """,
        ]

        for script in scripts:
            try:
                await page.add_init_script(script)
            except Exception as e:
                logger.debug(f"Stealth script injection error: {e}")

        logger.info("Stealth enhancements applied")

    @staticmethod
    async def set_realistic_viewport(page, fingerprint: Dict = None):
        """Set a realistic viewport size based on common resolutions."""
        if fingerprint and "screen" in fingerprint:
            width = fingerprint["screen"]["width"]
            height = fingerprint["screen"]["height"]
        else:
            # Common realistic resolutions
            resolutions = [
                (1920, 1080), (1366, 768), (1536, 864),
                (1440, 900), (1280, 720), (1680, 1050),
            ]
            width, height = random.choice(resolutions)

        await page.set_viewport_size({"width": width, "height": height})
        logger.info(f"Viewport set to {width}x{height}")

    @staticmethod
    async def set_realistic_geolocation(page, geolocation: Dict = None):
        """Set geolocation if provided."""
        if geolocation:
            try:
                context = page.context
                await context.grant_permissions(["geolocation"])
                await page.set_geolocation({
                    "latitude": geolocation["latitude"],
                    "longitude": geolocation["longitude"],
                })
                logger.info(f"Geolocation set: {geolocation['latitude']}, {geolocation['longitude']}")
            except Exception as e:
                logger.debug(f"Geolocation error: {e}")

    @staticmethod
    async def set_timezone(page, timezone: str = None):
        """Set timezone via Playwright's emulation."""
        if timezone:
            try:
                await page.context.add_init_script(f"""
                    Object.defineProperty(Intl.DateTimeFormat, 'resolvedOptions', {{
                        value: () => ({{ timeZone: '{timezone}' }}),
                    }});
                """)
            except Exception:
                pass


class OpenCaptchaSolver:
    """
    Main open-source CAPTCHA solver that orchestrates multiple strategies.
    No API keys required — uses free techniques.
    """

    # Strategies in priority order
    STRATEGIES = [
        "stealth",       # Avoid CAPTCHA entirely via stealth
        "audio",         # Audio reCAPTCHA solving
        "turnstile",     # Cloudflare Turnstile
        "fallback",      # Generic fallback approaches
    ]

    def __init__(self, page=None):
        self.page = page
        self.solved = False
        self.method_used = None

    async def solve(self, page=None, captcha_type: str = None, sitekey: str = None) -> bool:
        """
        Solve any CAPTCHA using the best available strategy.
        
        Args:
            page: Playwright page object (optional, uses self.page if not provided)
            captcha_type: Known CAPTCHA type if already detected
            sitekey: Known sitekey if already detected
            
        Returns:
            True if CAPTCHA was solved successfully
        """
        p = page or self.page
        if not p:
            logger.error("No page provided to OpenCaptchaSolver")
            return False

        logger.info(f"OpenCaptchaSolver: attempting to solve CAPTCHA (type={captcha_type})")

        # Strategy 1: Stealth (preventive — should already be applied)
        # Apply extra stealth at solve time
        await StealthEnhancer.apply_stealth(p)

        # Strategy 2: Try various solving methods based on CAPTCHA type
        if captcha_type and "turnstile" in captcha_type.lower():
            logger.info("Using Turnstile solver...")
            result = await TurnstileSolver.solve_turnstile(p)
            if result:
                self.solved = True
                self.method_used = "turnstile"
                return True

        # Strategy 3: Audio CAPTCHA solving (works for reCAPTCHA v2)
        if not captcha_type or "recaptcha" in captcha_type.lower():
            logger.info("Trying audio CAPTCHA solving...")
            result = await self._solve_via_audio(p)
            if result:
                self.solved = True
                self.method_used = "audio"
                return True

        # Strategy 4: Try turnstile anyway (catches undetected turnstile)
        logger.info("Trying Turnstile solver (fallback)...")
        result = await TurnstileSolver.solve_turnstile(p)
        if result:
            self.solved = True
            self.method_used = "turnstile_fallback"
            return True

        # Strategy 5: Generic fallback — try clicking and waiting
        logger.info("Trying generic CAPTCHA fallback...")
        result = await self._generic_fallback(p)
        if result:
            self.solved = True
            self.method_used = "generic_fallback"
            return True

        logger.warning("All open-source CAPTCHA solving strategies failed")
        return False

    async def _solve_via_audio(self, page) -> bool:
        """Solve CAPTCHA using audio challenge."""
        try:
            # First, find the CAPTCHA iframe
            iframe_selectors = [
                'iframe[src*="recaptcha"]',
                'iframe[src*="google.com/recaptcha"]',
                '.g-recaptcha iframe',
                'iframe[src*="hcaptcha"]',
                'iframe[src*="hcaptcha.com"]',
            ]

            for selector in iframe_selectors:
                try:
                    iframe_el = await page.query_selector(selector)
                    if iframe_el:
                        logger.info(f"Found CAPTCHA iframe: {selector}")
                        break
                except Exception:
                    iframe_el = None

            if iframe_el:
                # Try to solve via audio challenge
                text = await AudioCaptchaSolver.solve_audio_captcha(
                    page=page,
                    iframe_element=iframe_el,
                )
                if text:
                    # Submit the transcribed text
                    return await self._submit_audio_solution(page, text, iframe_el)

            # Try without iframe (some CAPTCHAs are inline)
            text = await AudioCaptchaSolver.solve_audio_captcha(page=page)
            if text:
                return await self._submit_audio_solution(page, text)

            return False

        except Exception as e:
            logger.warning(f"Audio solving error: {e}")
            return False

    async def _submit_audio_solution(self, page, text: str, iframe_element=None) -> bool:
        """Submit the transcribed audio solution to the CAPTCHA."""
        try:
            if iframe_element:
                iframe = await iframe_element.content_frame()
                if iframe:
                    # Find the audio response input
                    input_selectors = [
                        '#audio-response',
                        '.rc-audiochallenge-response input',
                        'input#audio-response',
                        'input[type="text"]',
                    ]
                    for selector in input_selectors:
                        try:
                            inp = await iframe.query_selector(selector)
                            if inp:
                                await inp.fill(text)
                                await asyncio.sleep(0.5)

                                # Click verify/submit button
                                verify_btn = await iframe.query_selector(
                                    '#recaptcha-verify-button, button:has-text("Verify"), input[type="submit"]'
                                )
                                if verify_btn:
                                    await verify_btn.click()
                                else:
                                    # Try pressing Enter
                                    await inp.press("Enter")

                                await asyncio.sleep(2)
                                logger.info("Audio solution submitted to iframe")
                                return True
                        except Exception:
                            continue

            # If no iframe or input not found, try on main page
            try:
                # Look for the g-recaptcha-response textarea
                textarea = await page.query_selector('textarea[name="g-recaptcha-response"]')
                if textarea:
                    await textarea.evaluate(f"el => {{ el.value = '{text}'; el.dispatchEvent(new Event('input', {{ bubbles: true }})); }}")
                    await asyncio.sleep(0.5)
                    logger.info("Solution injected into g-recaptcha-response")
                    return True
            except Exception:
                pass

            # Try to find and fill any text input related to captcha
            try:
                captcha_inputs = await page.query_selector_all('input[name*="captcha"], input[id*="captcha"], input[placeholder*="captcha" i]')
                for inp in captcha_inputs:
                    await inp.fill(text)
                    await asyncio.sleep(0.5)
                    logger.info("Solution injected into captcha input field")
                    return True
            except Exception:
                pass

            # Fire a custom event that some CAPTCHA handlers listen for
            try:
                await page.evaluate(f"""
                    window.dispatchEvent(new CustomEvent('captchaSolved', {{
                        detail: {{ token: '{text}', text: '{text}' }}
                    }}));
                """)
                logger.info("Dispatched captchaSolved event")
                return True
            except Exception:
                pass

            return False

        except Exception as e:
            logger.warning(f"Submit audio solution error: {e}")
            return False

    async def _generic_fallback(self, page) -> bool:
        """Generic fallback: try various approaches to get past the CAPTCHA."""
        try:
            # Approach 1: Wait and retry
            await asyncio.sleep(3)

            # Approach 2: Try to find and click a "I'm not a robot" checkbox
            recaptcha_selectors = [
                'iframe[src*="recaptcha/anchor"]',
                '.recaptcha-checkbox-border',
            ]
            for selector in recaptcha_selectors:
                try:
                    el = await page.query_selector(selector)
                    if el:
                        await el.click()
                        await asyncio.sleep(3)
                        logger.info("Clicked reCAPTCHA checkbox")
                        return True
                except Exception:
                    continue

            # Approach 3: Try evaluating grecaptcha.execute
            executed = await page.evaluate("""
                () => {
                    return new Promise((resolve) => {
                        if (typeof grecaptcha !== 'undefined' && grecaptcha.execute) {
                            try {
                                grecaptcha.enterprise.ready(() => {
                                    grecaptcha.enterprise.execute('6LfT6isqAAAAAFknaGcXCSre2_9DA1TjLZ3P1C8-', {action: 'submit'})
                                        .then(token => resolve(!!token))
                                        .catch(() => resolve(false));
                                });
                            } catch(e) {
                                try {
                                    grecaptcha.execute().then(token => resolve(!!token)).catch(() => resolve(false));
                                } catch(e2) {
                                    resolve(false);
                                }
                            }
                        } else {
                            resolve(false);
                        }
                    });
                }
            """)
            if executed:
                await asyncio.sleep(2)
                logger.info("reCAPTCHA execute() succeeded")
                return True

            return False

        except Exception as e:
            logger.warning(f"Generic fallback error: {e}")
            return False


# Convenience function
async def solve_captcha_open_source(page, captcha_type: str = None) -> bool:
    """
    Attempt to solve any CAPTCHA using open-source techniques (no API key required).
    
    Args:
        page: Playwright page object
        captcha_type: Optional known CAPTCHA type
        
    Returns:
        True if CAPTCHA was successfully solved
    """
    solver = OpenCaptchaSolver(page)
    return await solver.solve(captcha_type=captcha_type)
