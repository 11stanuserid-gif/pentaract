# =============================================================================
# DEVICE FINGERPRINT GENERATOR
# Generates unique device fingerprints for each test session
# =============================================================================

import random
from typing import Dict, Optional
from fake_useragent import UserAgent


class FingerprintGenerator:
    """Generates realistic device fingerprints to test detection systems."""

    SCREEN_RESOLUTIONS = [
        (1920, 1080), (1366, 768), (1536, 864), (1440, 900),
        (1280, 720), (2560, 1440), (1680, 1050), (1600, 900),
        (3840, 2160), (1280, 800), (1920, 1200), (1024, 768),
    ]

    PLATFORMS = ["Win32", "MacIntel", "Linux x86_64"]

    LANGUAGES = ["en-IN", "en-US", "en-GB", "hi-IN"]

    HARDWARE_CONCURRENCY = [2, 4, 6, 8, 12, 16]

    DEVICE_MEMORY = [2, 4, 8, 16, 32]

    WEBGL_VENDORS = [
        "Intel Inc.",
        "NVIDIA Corporation",
        "AMD",
        "Apple Inc.",
    ]

    WEBGL_RENDERERS = [
        "Intel Iris Xe Graphics",
        "NVIDIA GeForce GTX 1650",
        "AMD Radeon RX 580",
        "Intel UHD Graphics 620",
        "NVIDIA GeForce RTX 3060",
        "AMD Radeon RX 6700 XT",
        "NVIDIA GeForce RTX 3070",
        "Intel UHD Graphics 630",
        "AMD Radeon RX 6600",
        "NVIDIA GeForce GTX 1060",
        "Apple M1 GPU",
        "Apple M2 GPU",
        "NVIDIA GeForce RTX 4090",
        "AMD Radeon RX 7900 XT",
    ]

    TIMEZONES = [
        "Asia/Kolkata",
        "Asia/Dubai",
        "Asia/Singapore",
        "Asia/Bangkok",
        "Asia/Jakarta",
    ]

    INDIAN_IP_RANGES = [
        (103, 21, 103, 255), (106, 66, 106, 220),
        (111, 91, 111, 125), (115, 96, 115, 255),
        (117, 96, 117, 255), (122, 162, 122, 180),
        (124, 124, 124, 255), (14, 96, 14, 195),
        (27, 34, 27, 122), (49, 32, 49, 255),
        (59, 88, 59, 185), (61, 16, 61, 17),
    ]

    def __init__(self):
        try:
            self.ua = UserAgent(fallback="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        except Exception:
            self.ua = None

    def generate_screen(self) -> Dict:
        """Generate screen properties."""
        width, height = random.choice(self.SCREEN_RESOLUTIONS)
        return {
            "width": width,
            "height": height,
            "color_depth": random.choice([24, 32]),
            "pixel_ratio": random.choice([1, 1.25, 1.5, 2]),
            "avail_width": width - random.choice([0, 8]),
            "avail_height": height - random.choice([40, 48, 72]),
        }

    def generate_browser(self) -> Dict:
        """Generate browser properties."""
        if self.ua:
            try:
                user_agent = self.ua.random
            except Exception:
                user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        else:
            user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

        platform = random.choice(self.PLATFORMS)

        # Build platform-specific user agent if needed
        if "Windows" not in user_agent and "Mac" not in user_agent and "Linux" not in user_agent:
            if platform == "Win32":
                user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            elif platform == "MacIntel":
                user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            else:
                user_agent = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

        return {
            "user_agent": user_agent,
            "platform": platform,
            "language": random.choice(self.LANGUAGES),
            "languages": [random.choice(self.LANGUAGES), "en"],
            "hardware_concurrency": random.choice(self.HARDWARE_CONCURRENCY),
            "device_memory": random.choice(self.DEVICE_MEMORY),
            "touch_support": random.choice([True, False]),
            "cookie_enabled": True,
            "pdf_viewer_enabled": True,
        }

    def generate_webgl(self) -> Dict:
        """Generate WebGL fingerprint."""
        vendor = random.choice(self.WEBGL_VENDORS)

        # Match renderer to vendor
        if vendor == "Intel Inc.":
            renderer = random.choice([
                "Intel Iris Xe Graphics",
                "Intel UHD Graphics 620",
                "Intel UHD Graphics 630",
                "Intel HD Graphics 530",
            ])
        elif vendor == "NVIDIA Corporation":
            renderer = random.choice([
                "NVIDIA GeForce GTX 1650",
                "NVIDIA GeForce RTX 3060",
                "NVIDIA GeForce RTX 3070",
                "NVIDIA GeForce GTX 1060",
                "NVIDIA GeForce RTX 4090",
                "NVIDIA GeForce RTX 3080",
            ])
        elif vendor == "Apple Inc.":
            renderer = random.choice([
                "Apple M1 GPU",
                "Apple M2 GPU",
                "Apple M3 GPU",
            ])
        else:
            renderer = random.choice([
                "AMD Radeon RX 580",
                "AMD Radeon RX 6700 XT",
                "AMD Radeon RX 6600",
                "AMD Radeon RX 7900 XT",
            ])

        return {
            "vendor": vendor,
            "renderer": renderer,
        }

    def generate_timezone(self) -> Dict:
        """Generate timezone information."""
        tz = random.choice(self.TIMEZONES)

        # Get offset for timezone
        tz_offsets = {
            "Asia/Kolkata": "+05:30",
            "Asia/Dubai": "+04:00",
            "Asia/Singapore": "+08:00",
            "Asia/Bangkok": "+07:00",
            "Asia/Jakarta": "+07:00",
        }

        return {
            "timezone": tz,
            "offset": tz_offsets.get(tz, "+05:30"),
        }

    def generate_ip(self) -> Optional[str]:
        """Generate a realistic Indian IP address."""
        ip_range = random.choice(self.INDIAN_IP_RANGES)
        a_start, b_start, a_end, b_end = ip_range

        a = random.randint(a_start, a_end)

        if a == a_start:
            b = random.randint(b_start, 255)
        elif a == a_end:
            b = random.randint(0, b_end)
        else:
            b = random.randint(0, 255)

        c = random.randint(0, 255)
        d = random.randint(1, 254)

        return f"{a}.{b}.{c}.{d}"

    def generate_plugins(self) -> list:
        """Generate browser plugins list."""
        plugin_count = random.choice([2, 3, 4, 5])
        plugins = []
        for i in range(plugin_count):
            plugins.append({
                "name": f"Plugin {i+1}",
                "description": f"Description for plugin {i+1}",
                "version": f"{random.randint(1, 5)}.{random.randint(0, 9)}.{random.randint(0, 9)}",
            })
        return plugins

    def generate_fingerprint(self) -> Dict:
        """Generate a complete device fingerprint."""
        return {
            "screen": self.generate_screen(),
            "browser": self.generate_browser(),
            "webgl": self.generate_webgl(),
            "timezone": self.generate_timezone(),
            "ip": self.generate_ip(),
            "plugins": self.generate_plugins(),
        }

    def get_browser_launch_args(self, fingerprint: Dict, proxy: Optional[str] = None) -> list:
        """Generate Chrome browser launch arguments based on fingerprint."""
        screen = fingerprint["screen"]

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
            f"--lang={fingerprint['browser']['language']},en",
            f"--window-size={screen['width']},{screen['height']}",
            f"--force-device-scale-factor={screen['pixel_ratio']}",
            f"--user-agent={fingerprint['browser']['user_agent']}",
        ]

        if proxy:
            args.append(f"--proxy-server={proxy}")

        return args

    def get_context_options(self, fingerprint: Dict) -> Dict:
        """Generate browser context options based on fingerprint."""
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
            "geolocation": None,  # Will be set per-identity
            "permissions": ["geolocation"],
            "color_scheme": "light",
            "reduced_motion": "no-preference",
            "device_scale_factor": screen["pixel_ratio"],
            "is_mobile": False,
            "has_touch": browser["touch_support"],
        }
