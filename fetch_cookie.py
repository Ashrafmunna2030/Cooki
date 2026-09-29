import asyncio
import json
import requests
import os
from playwright.async_api import async_playwright

# আপনার User-Agent (UA) ভেরিয়েবল
UA = ("Mozilla/5.0 (Linux; Android 16; V2446 Build/BP2A.250605.031.A3; wv) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 "
      "Chrome/127.0.6533.144 Mobile Safari/537.36")

# আপনার টেলিগ্রাম বটের তথ্য
BOT_TOKEN = "8450441691:AAHrKs10fFE8TsO_7Okrjj8pn9_acanOEnc"
CHAT_ID = "-1004322570598"

# টার্গেট এবং API এন্ডপয়েন্ট
TARGET_URL = "https://shop.garena.my/?channel=202953"
API_ENDPOINT = "https://shop.garena.my/api/preflight"
JSON_FILE = "cooxkie.json"


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


def format_simple_cookies(raw_cookies, current_id):
    """
    শুধুমাত্র ID এবং কুকির Key:Value গুলো সেভ করবে।
    """
    result = {"id": current_id}
    
    # সব কুকি যুক্ত করা হচ্ছে
    for c in raw_cookies:
        result[c["name"]] = c["value"]

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

            # এখানে আপনার দেওয়া UA ভেরিয়েবলটি ব্যবহার করা হয়েছে
            context = await browser.new_context(
                user_agent=UA
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

            # 🎯 সিরিয়াল আইডি (1, 2, 3...) বের করা
            existing_data = []
            next_id = 1
            
            if os.path.exists(JSON_FILE):
                try:
                    with open(JSON_FILE, "r", encoding="utf-8") as f:
                        content = f.read().strip()
                        if content:
                            existing_data = json.loads(content)
                            if isinstance(existing_data, list) and len(existing_data) > 0:
                                next_id = existing_data[-1].get("id", 0) + 1
                            elif isinstance(existing_data, dict):
                                next_id = existing_data.get("id", 0) + 1
                                existing_data = [existing_data] 
                except json.JSONDecodeError:
                    print("পুরানো JSON ফাইলে সমস্যা, নতুন করে তৈরি করা হচ্ছে...")
                    existing_data = []

            # 🎯 সিম্পল JSON বানানো
            new_cookie_entry = format_simple_cookies(raw_cookies, next_id)
            existing_data.append(new_cookie_entry)
            
            # 📁 JSON ফাইলে সেভ করা
            with open(JSON_FILE, "w", encoding="utf-8") as f:
                json.dump(existing_data, f, indent=4, ensure_ascii=False)

            # 📤 Telegram এ মেসেজ পাঠানো
            telegram_display_json = json.dumps(new_cookie_entry, indent=2, ensure_ascii=False)
            msg = (
                f"✅ <b>Cookie Fetched Successfully</b>\n"
                f"🆔 <b>Serial ID:</b> {next_id}\n"
                f"🍪 Total Cookies: {len(raw_cookies)}\n\n"
                f"<pre>{telegram_display_json}</pre>"
            )
            send_telegram_message(msg)

            print(f"কাজ শেষ! ডেটা {JSON_FILE} এ ID: {next_id} হিসেবে সেভ হয়েছে।")
            await browser.close()

    except Exception as e:
        error_msg = f"❌ <b>স্ক্রিপ্ট রান করতে সমস্যা:</b>\n<code>{str(e)}</code>"
        print(error_msg)
        send_telegram_message(error_msg)


if __name__ == "__main__":
    asyncio.run(fetch_all_data())
