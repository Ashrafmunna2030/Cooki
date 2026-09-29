import asyncio
import json
import requests
import os
from datetime import datetime
from playwright.async_api import async_playwright

# আপনার টেলিগ্রাম বটের তথ্য
BOT_TOKEN = "8450441691:AAHrKs10fFE8TsO_7Okrjj8pn9_acanOEnc"
CHAT_ID = "-1004322570598"

# টার্গেট এবং API এন্ডপয়েন্ট
TARGET_URL = "https://shop.garena.my/?channel=202953"
API_ENDPOINT = "https://shop.garena.my/api/preflight"
JSON_FILE = "cookie.json"


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


def format_all_cookies(raw_cookies, current_id):
    """
    Playwright থেকে পাওয়া সব কুকি (A to Z) একটি প্রিমিয়াম JSON স্ট্রাকচারে সাজাবে।
    সাথে সিরিয়াল ID থাকবে।
    """
    cookie_dict = {c["name"]: c["value"] for c in raw_cookies}

    result = {
        "id": current_id,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "metadata": {
            "source": "pc",
            "region": "MY",
            "language": "en",
            "total_cookies": len(raw_cookies)
        },
        "cookies_dict": cookie_dict,        
        "cookies_raw_array": raw_cookies    
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

            # 🎯 সিরিয়াল আইডি (1, 2, 3...) বের করা এবং পুরানো ডেটা লোড করার লজিক
            existing_data = []
            next_id = 1
            
            if os.path.exists(JSON_FILE):
                try:
                    with open(JSON_FILE, "r", encoding="utf-8") as f:
                        content = f.read().strip()
                        if content:
                            existing_data = json.loads(content)
                            # যদি ডেটা লিস্ট আকারে থাকে (একাধিক সেভ করা ডেটা)
                            if isinstance(existing_data, list) and len(existing_data) > 0:
                                next_id = existing_data[-1].get("id", 0) + 1
                            # যদি পুরানো ডেটা ডিকশনারি আকারে থাকে (আগের কোডের কারণে)
                            elif isinstance(existing_data, dict):
                                next_id = existing_data.get("id", 0) + 1
                                existing_data = [existing_data] 
                except json.JSONDecodeError:
                    print("পুরানো JSON ফাইলে সমস্যা, নতুন করে তৈরি করা হচ্ছে...")
                    existing_data = []

            # 🎯 A to Z কুকি নিয়ে প্রিমিয়াম JSON বানানো (নতুন ID সহ)
            new_cookie_entry = format_all_cookies(raw_cookies, next_id)
            existing_data.append(new_cookie_entry)
            
            # 📁 JSON ফাইলে সেভ করা (পুরানো + নতুন ডেটা)
            with open(JSON_FILE, "w", encoding="utf-8") as f:
                json.dump(existing_data, f, indent=4, ensure_ascii=False)

            # 📤 Telegram এ মেসেজ পাঠানো
            telegram_display_json = json.dumps(new_cookie_entry["cookies_dict"], indent=2, ensure_ascii=False)
            msg = (
                f"✅ <b>Cookie Fetched Successfully</b>\n"
                f"🆔 <b>Serial ID:</b> {next_id}\n"
                f"🍪 Total Cookies: {len(raw_cookies)}\n\n"
                f"<pre>{telegram_display_json}</pre>"
            )
            send_telegram_message(msg)

            print(f"কাজ শেষ! ডেটা {JSON_FILE} এ ID: {next_id} হিসেবে সেভ হয়েছে। ব্রাউজার বন্ধ করা হচ্ছে...")
            await browser.close()

    except Exception as e:
        error_msg = f"❌ <b>স্ক্রিপ্ট রান করতে সমস্যা:</b>\n<code>{str(e)}</code>"
        print(error_msg)
        send_telegram_message(error_msg)


if __name__ == "__main__":
    asyncio.run(fetch_all_data())
