import asyncio
import json
import requests
import os
from playwright.async_api import async_playwright

# আপনার টেলিগ্রাম বটের তথ্য
BOT_TOKEN = "8450441691:AAHrKs10fFE8TsO_7Okrjj8pn9_acanOEnc"
CHAT_ID = "-1004322570598"

# টার্গেট এবং API এন্ডপয়েন্ট
TARGET_URL = "https://shop.garena.my/?channel=202953"
API_ENDPOINT = "https://shop.garena.my/api/preflight"

# ⚙️ Supabase কনফিগারেশন
SUPABASE_URL = os.environ.get(
    "SUPABASE_URL",
    "https://ocxfmewaxffywmxegzwo.supabase.co"
)
SUPABASE_SECRET_KEY = os.environ.get(
    "SUPABASE_SECRET_KEY",
    "sb_secret_fXVg0apSaLvLdpFxgaY4Dw_y7hwA2tr"
)


def send_telegram_alert(message, file_path=None):
    try:
        if file_path and os.path.exists(file_path):
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
            with open(file_path, 'rb') as f:
                requests.post(
                    url,
                    data={'chat_id': CHAT_ID, 'caption': message},
                    files={'document': f}
                )
        else:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            requests.post(
                url,
                json={'chat_id': CHAT_ID, 'text': message, 'parse_mode': 'HTML'}
            )
    except Exception as e:
        print(f"Telegram alert error: {e}")


def save_to_supabase(all_data):
    """Supabase এ ডেটা সেভ করে"""
    try:
        url = f"{SUPABASE_URL}/rest/v1/cookie_data"
        headers = {
            "apikey": SUPABASE_SECRET_KEY,
            "Authorization": f"Bearer {SUPABASE_SECRET_KEY}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal"
        }

        payload = {
            "data": all_data,
            "cookie_count": len(all_data.get("cookies", []))
        }

        response = requests.post(url, headers=headers, json=payload, timeout=20)

        if response.status_code in (200, 201, 204):
            print("✅ Supabase এ ডেটা সেভ হয়েছে!")
            return True
        else:
            print(f"❌ Supabase error: {response.status_code} - {response.text[:300]}")
            return False

    except Exception as e:
        print(f"❌ Supabase save error: {e}")
        return False


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

            api_data = None
            if api_response.ok:
                print("✅ API রেসপন্স সফলভাবে পাওয়া গেছে!")
                try:
                    api_data = await api_response.json()
                except Exception:
                    api_data = {"raw": await api_response.text()}
            else:
                print(f"❌ API Error: স্ট্যাটাস কোড {api_response.status}")
                api_data = {"error": f"Failed with status {api_response.status}"}

            print("কুকি এক্সট্র্যাক্ট করা হচ্ছে...")
            cookies = await context.cookies()

            all_data = {
                "api_response": api_data,
                "cookies": cookies
            }

            # 📤 Supabase এ সেভ
            print("Supabase এ সেভ করা হচ্ছে...")
            db_success = save_to_supabase(all_data)

            # 📁 Local backup
            with open("all_data.json", "w", encoding="utf-8") as f:
                json.dump(all_data, f, indent=4, ensure_ascii=False)

            msg = f"✅ <b>সফলভাবে ডেটা পাওয়া গেছে!</b>\n\n"
            msg += f"🍪 মোট কুকি: {len(cookies)}\n"
            msg += f"💾 Database: {'✅ সেভ হয়েছে' if db_success else '❌ ব্যর্থ'}"

            send_telegram_alert(msg, file_path="all_data.json")
            print("কাজ শেষ! ব্রাউজার বন্ধ করা হচ্ছে...")

            await browser.close()

    except Exception as e:
        error_msg = f"❌ স্ক্রিপ্ট রান করতে সমস্যা হয়েছে:\n<code>{str(e)}</code>"
        print(error_msg)
        send_telegram_alert(error_msg)


if __name__ == "__main__":
    asyncio.run(fetch_all_data())
