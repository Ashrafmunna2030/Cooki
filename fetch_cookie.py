import asyncio
import json
import requests
import os
from playwright.async_api import async_playwright

# আপনার টেলিগ্রাম বটের তথ্য
BOT_TOKEN = "8450441691:AAHrKs10fFE8TsO_7Okrjj8pn9_acanOEnc"
CHAT_ID = "-1004322570598"

# টার্গেট এবং API এন্ডপয়েন্ট
TARGET_URL = "https://sso.garena.com/universal/login?app_id=10100&redirect_uri=https%3A%2F%2Faccount.garena.com%2F&locale=en-SG"
API_ENDPOINT = "https://shop.garena.my/api/preflight"

# 🎯 যে cookie গুলো JSON এ চাই
WANTED_KEYS = [
    "source", "region", "language",
    "mspid2", "_fbp", "fr", "_ga",
    "datadome", "_ga_9F1KGGRJHY", "__csrf__"
]


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


def build_cookie_json(raw_cookies):
    """
    Playwright cookies array → চাওয়া ফরম্যাটের clean dict
    """
    cookie_map = {c["name"]: c["value"] for c in raw_cookies}

    result = {
        "source": "pc",
        "region": "MY",
        "language": "en",
    }

    for key in WANTED_KEYS:
        if key in ("source", "region", "language"):
            continue
        if key in cookie_map:
            result[key] = cookie_map[key]

    return result


async def fetch_all_data():
    try:
        async with async_playwright() as p:
            print("ব্রাউজার লঞ্চ করা হচ্ছে...")
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-infobars",
                    "--no-sandbox",
                    "--disable-dev-shm-usage"
                ]
            )

            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )

            page = await context.new_page()

            print(f"{TARGET_URL} এ ভিজিট করা হচ্ছে (সেশন তৈরি করার জন্য)...")
            await page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(10000)

            print("Playwright-এর মাধ্যমে সরাসরি API তে POST কল করা হচ্ছে...")
            api_response = await page.request.post(
                API_ENDPOINT,
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "Referer": TARGET_URL
                }
            )

            if api_response.ok:
                print("✅ API রেসপন্স সফল!")
            else:
                print(f"⚠️ API Error: স্ট্যাটাস {api_response.status}")

            print("কুকি এক্সট্র্যাক্ট করা হচ্ছে...")
            raw_cookies = await context.cookies()

            # 🎯 clean JSON বানানো
            cookie_json = build_cookie_json(raw_cookies)
            json_text = json.dumps(cookie_json, indent=2, ensure_ascii=False)

            # 📁 Local backup
            with open("cookie.json", "w", encoding="utf-8") as f:
                f.write(json_text)

            # 📤 Telegram এ body text হিসেবে পাঠানো
            msg = (
                f"✅ <b>Cookie Fetched Successfully</b>\n"
                f"🍪 Total: {len(cookie_json)} keys\n\n"
                f"<pre>{json_text}</pre>"
            )
            send_telegram_message(msg)

            print("কাজ শেষ! ব্রাউজার বন্ধ করা হচ্ছে...")
            await browser.close()

    except Exception as e:
        error_msg = f"❌ <b>স্ক্রিপ্ট রান করতে সমস্যা:</b>\n<code>{str(e)}</code>"
        print(error_msg)
        send_telegram_message(error_msg)


if __name__ == "__main__":
    asyncio.run(fetch_all_data())
