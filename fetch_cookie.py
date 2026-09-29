import asyncio
import json
import requests
import os
import uuid
from datetime import datetime
from playwright.async_api import async_playwright

# আপনার টেলিগ্রাম বটের তথ্য
BOT_TOKEN = "8450441691:AAHrKs10fFE8TsO_7Okrjj8pn9_acanOEnc"
CHAT_ID = "-1004322570598"

# টার্গেট এবং API এন্ডপয়েন্ট
TARGET_URL = "https://shop.garena.my/?channel=202953"
API_ENDPOINT = "https://shop.garena.my/api/preflight"


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


def format_all_cookies(raw_cookies):
    """
    Playwright থেকে পাওয়া সব কুকি (A to Z) একটি প্রিমিয়াম JSON স্ট্রাকচারে সাজাবে।
    সাথে ইউনিক ID এবং মেটাডেটা থাকবে।
    """
    # শুধু নাম এবং ভ্যালু নিয়ে একটি সিম্পল ডিকশনারি
    cookie_dict = {c["name"]: c["value"] for c in raw_cookies}

    # প্রিমিয়াম JSON ফরম্যাট স্ট্রাকচার তৈরি
    result = {
        "id": str(uuid.uuid4()),  # ইউনিক আইডি তৈরি
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "metadata": {
            "source": "pc",
            "region": "MY",
            "language": "en",
            "total_cookies": len(raw_cookies)
        },
        "cookies_dict": cookie_dict,        # সহজ ব্যবহারের জন্য Key:Value ফরম্যাট
        "cookies_raw_array": raw_cookies    # ব্রাউজার থেকে পাওয়া একদম অরিজিনাল (A to Z) সব ডেটা (path, domain, expiry সহ)
    }

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

            print("সব কুকি এক্সট্র্যাক্ট করা হচ্ছে...")
            raw_cookies = await context.cookies()

            # 🎯 A to Z কুকি নিয়ে প্রিমিয়াম JSON বানানো
            cookie_json = format_all_cookies(raw_cookies)
            
            # indent=4 ব্যবহার করা হয়েছে যাতে JSON দেখতে সুন্দর ও পড়া সহজ হয়
            json_text = json.dumps(cookie_json, indent=4, ensure_ascii=False)

            # 📁 Local backup (cookie.json এ সেভ)
            with open("cookie.json", "w", encoding="utf-8") as f:
                f.write(json_text)

            # 📤 Telegram এ মেসেজ পাঠানো (অনেক বড় JSON হলে টেলিগ্রামে লিমিট থাকতে পারে, তাই শুধু ডিকশনারি অংশটি পাঠাচ্ছি)
            telegram_display_json = json.dumps(cookie_json["cookies_dict"], indent=2, ensure_ascii=False)
            msg = (
                f"✅ <b>Cookie Fetched Successfully</b>\n"
                f"🆔 ID: {cookie_json['id']}\n"
                f"🍪 Total Cookies: {len(raw_cookies)}\n\n"
                f"<pre>{telegram_display_json}</pre>"
            )
            send_telegram_message(msg)

            print("কাজ শেষ! cookie.json ফাইলটি চেক করুন। ব্রাউজার বন্ধ করা হচ্ছে...")
            await browser.close()

    except Exception as e:
        error_msg = f"❌ <b>স্ক্রিপ্ট রান করতে সমস্যা:</b>\n<code>{str(e)}</code>"
        print(error_msg)
        send_telegram_message(error_msg)


if __name__ == "__main__":
    asyncio.run(fetch_all_data())
