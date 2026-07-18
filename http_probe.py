#!/usr/bin/env python3
"""Direct HTTP approach to genspark signup"""
import requests
import re
import json

session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
})

# Step 1: Navigate to login page
print("=== Step 1: GET /login ===")
r = session.get('https://www.genspark.ai/login', allow_redirects=True)
print(f"Status: {r.status_code}")
print(f"URL: {r.url}")
print(f"Cookies: {dict(session.cookies)}")

# Check if we got a nuxt page with the authorize redirect
if 'b2clogin.com' in r.text or 'login.genspark.ai' in r.text:
    print("Found Azure B2C reference in login page")
    
    # Extract the redirect URL from the page
    # Nuxt might have the URL in a script tag
    import re
    auth_urls = re.findall(r'https?://[^"\'\\]*b2clogin\.com[^"\'\\]*', r.text)
    if auth_urls:
        print(f"Found B2C URL: {auth_urls[0][:150]}")
    
    login_urls = re.findall(r'https?://[^"\'\\]*login\.genspark\.ai[^"\'\\]*', r.text)
    if login_urls:
        print(f"Found login.genspark URL: {login_urls[0][:150]}")

# Step 2: Look for the actual Azure B2C authorize URL in the HTML
# Usually it's in a script tag or a meta refresh
auth_url_match = re.search(r'window\.location\s*=\s*["\']([^"\']+)["\']', r.text)
if auth_url_match:
    print(f"Redirect URL found: {auth_url_match.group(1)[:150]}")

# Try to extract all URLs in the page
all_urls = re.findall(r'https?://[\w./?=&%-]+', r.text)
for u in all_urls:
    if 'authorize' in u or 'b2c' in u or 'login' in u:
        print(f"Found URL: {u[:200]}")
