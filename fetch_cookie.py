#!/usr/bin/env python3
# ============================================================================
# ⚡ GARENA COOKIE FETCHER (Playwright · Mobile UA · No Preset Cookies) ⚡
# Fetches fresh cookies from shop.garena.my and sends to Telegram
# ============================================================================

import asyncio
import json
import requests
import os
from playwright.async_api import async_playwright

# ============================================================================
# TELEGRAM CONFIG
# ============================================================================
BOT_TOKEN = "8450441691:AAHrKs10fFE8TsO_7Okrjj8pn9_acanOEnc"
CHAT_ID   = "-1004322570598"

# ============================================================================
# TARGET
# ============================================================================
TARGET_URL   = "https://shop.garena.my/?channel=202953"
API_ENDPOINT = "https://shop.garena.my/api/preflight"

# ============================================================================
# ✅ MOBILE UA — Android WebView (A to Z)
# ============================================================================
UA = "Mozilla/5.0 (Linux; Android 12; M2101K7AI Build/SKQ1.210908.001) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.8010.36 Mobile Safari/537.36"

# ============================================================================
# ✅ MOBILE BASE HEADERS — applied globally to every request
# ============================================================================
BASE_HEADERS = {
    "sec-ch-ua-platform": '"Android"',
    "sec-ch-ua": '"Android WebView";v="153", "Not_A Brand";v="8", "Chromium";v="153"',
    "sec-ch-ua-mobile": "?1",
    "X-Requested-With": "mark.via.gp",
    "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8",
}

# ============================================================================
# 🎯 Wanted cookie keys (output JSON format)
# ============================================================================
WANTED_KEYS = [
    "source", "region", "language",
    "mspid2", "_fbp", "fr", "_ga",
    "datadome", "_ga_9F1KGGRJHY", "__csrf__"
]


# ============================================================================
# TELEGRAM SENDER
# ============================================================================
def send_telegram_message(message):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        requests.post(
            url,
            json={
                'chat_id': CHAT_ID,
                'text': message,
                'parse_mode': 'HTML',
                'disable_web_page_preview': True
            },
            timeout=20
        )
    except Exception as e:
        print(f"Telegram alert error: {e}")


# ============================================================================
# BUILD CLEAN COOKIE JSON
# ============================================================================
def build_cookie_json(raw_cookies):
    """
    Playwright cookies array → clean dict (exactly the format the engine needs)
    """
    cookie_map = {c["name"]: c["value"] for c in raw_cookies}

    result = {
        "source":   "pc",
        "region":   "MY",
        "language": "en",
    }

    for key in WANTED_KEYS:
        if key in ("source", "region", "language"):
            continue
        if key in cookie_map:
            result[key] = cookie_map[key]

    return result


# ============================================================================
# MAIN — Playwright + Mobile UA + Mobile Headers
# ============================================================================
async def fetch_all_data():
    try:
        async with async_playwright() as p:
            print("🚀 Launching browser (Mobile UA)...")

            browser = await p.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-infobars",
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--no-first-run",
                    "--no-default-browser-check",
                ]
            )

            # ✅ Fresh context — NO preset cookies (fresh session jar)
            context = await browser.new_context(
                user_agent=UA,
                viewport={"width": 412, "height": 915},           # Android mobile viewport
                device_scale_factor=2.625,
                is_mobile=True,
                has_touch=True,
                locale="en-GB",
                timezone_id="Asia/Yangon",
                extra_http_headers=BASE_HEADERS,                  # ✅ Mobile headers globally
            )

            # ✅ NO preset cookies — fresh jar
            page = await context.new_page()

            print(f"🌐 Visiting {TARGET_URL} (to generate session)...")
            await page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(10000)

            # ================================================================
            # Trigger preflight API (like real browser)
            # ================================================================
            print("📡 Calling /api/preflight via browser context...")
            try:
                api_response = await page.request.post(
                    API_ENDPOINT,
                    headers={
                        "Accept": "application/json",
                        "Content-Type": "application/json",
                        "Referer": TARGET_URL,
                        "Origin": "https://shop.garena.my",
                    }
                )
                if api_response.ok:
                    print("✅ API response OK")
                else:
                    print(f"⚠️ API Error: status {api_response.status}")
            except Exception as e:
                print(f"⚠️ Preflight failed: {e}")

            # ================================================================
            # Extract cookies
            # ================================================================
            print("🍪 Extracting cookies...")
            raw_cookies = await context.cookies()

            cookie_json = build_cookie_json(raw_cookies)
            json_text = json.dumps(cookie_json, indent=2, ensure_ascii=False)

            # 📁 Local backup
            with open("cookie.json", "w", encoding="utf-8") as f:
                f.write(json_text)

            print(f"✅ Cookies fetched: {len(cookie_json)} keys")

            # 📤 Send to Telegram
            msg = (
                f"✅ <b>Cookie Fetched Successfully</b>\n"
                f"🤖 Mobile UA · Fresh Session\n"
                f"🍪 Total: {len(cookie_json)} keys\n\n"
                f"<pre>{json_text}</pre>"
            )
            send_telegram_message(msg)

            print("🔒 Closing browser...")
            await browser.close()

            return cookie_json

    except Exception as e:
        error_msg = f"❌ <b>Script Error:</b>\n<code>{str(e)}</code>"
        print(error_msg)
        send_telegram_message(error_msg)
        return None


# ============================================================================
# ENTRY POINT
# ============================================================================
if __name__ == "__main__":
    result = asyncio.run(fetch_all_data())
    if result:
        print("\n" + "=" * 70)
        print("COOKIE JSON:")
        print("=" * 70)
        print(json.dumps(result, indent=2, ensure_ascii=False))
