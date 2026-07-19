#!/usr/bin/env python3
"""Set Render env vars via dashboard automation"""
import asyncio
from playwright.async_api import async_playwright

RENDER_API_KEY = "rnd_sQcXvmFmNWqPo8Ka3QrFdjKlGVUU"
SERVICE_URL = "https://dashboard.render.com/web/srv-d9dl4r741pts73dcol8g/env-vars"

ENVS = {
    "PORT": "7860",
    "DATABASE_USER": "avnadmin",
    "DATABASE_PASSWORD": "AVNS_RLdM3I4ET4_4ozfXTcN",
    "DATABASE_NAME": "defaultdb",
    "DATABASE_HOST": "pg-752045-stanuserid-9476.a.aivencloud.com",
    "DATABASE_PORT": "26183",
    "WORKERS": "2",
    "CHANNEL_CAPACITY": "100",
    "SUPERUSER_EMAIL": "admin@pentaract.io",
    "SUPERUSER_PASS": "Px9kL2mN7vQ4wR8tY5uI1oP3sA6dF0gH",
    "ACCESS_TOKEN_EXPIRE_IN_SECS": "3600",
    "REFRESH_TOKEN_EXPIRE_IN_DAYS": "30",
    "SECRET_KEY": "bc117b7d93fafc8b78ddbb676916f84fdd0281305f8d052325d0922423374c01",
    "TELEGRAM_API_BASE_URL": "https://api.telegram.org",
    "TELEGRAM_RATE_LIMIT": "18",
}

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        # Login with API key
        await page.goto("https://dashboard.render.com/login")
        await page.wait_for_load_state("networkidle")

        # Try API key auth
        await page.goto(f"https://dashboard.render.com/")
        await page.wait_for_load_state("networkidle")

        # Set cookies/token for API key auth
        await context.add_cookies([{
            "name": "rnd_api_key",
            "value": RENDER_API_KEY,
            "domain": ".render.com",
            "path": "/"
        }])

        # Navigate to service env vars page
        await page.goto(SERVICE_URL)
        await page.wait_for_load_state("networkidle")

        print(f"Page title: {await page.title()}")
        print(f"Page URL: {page.url}")

        # Take a screenshot to see what's there
        await page.screenshot(path="/opt/render/render_dashboard.png")
        print("Screenshot saved to render_dashboard.png")

        await browser.close()

asyncio.run(main())
