import asyncio
import json
import requests
from playwright.async_api import async_playwright

# আপনার টেলিগ্রাম বটের তথ্য
BOT_TOKEN = "8450441691:AAHrKs10fFE8TsO_7Okrjj8pn9_acanOEnc"
CHAT_ID = "-1004322570598"

# উদাহরণ টার্গেট এবং API এন্ডপয়েন্ট (আপনার প্রয়োজন অনুযায়ী পরিবর্তন করে নিবেন)
TARGET_URL = "https://shop.garena.my/?channel=202953" 
API_ENDPOINT = "https://shop.garena.my/api/preflight" 

def send_telegram_alert(message, file_path=None):
    try:
        if file_path:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
            with open(file_path, 'rb') as f:
                requests.post(url, data={'chat_id': CHAT_ID, 'caption': message}, files={'document': f})
        else:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            requests.post(url, json={'chat_id': CHAT_ID, 'text': message, 'parse_mode': 'HTML'})
    except Exception as e:
        print(f"Telegram alert error: {e}")

async def fetch_all_data():
    try:
        async with async_playwright() as p:
            print("ব্রাউজার লঞ্চ করা হচ্ছে...")
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-infobars"
                ]
            )
            
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            
            page = await context.new_page()

            print(f"{TARGET_URL} এ ভিজিট করা হচ্ছে (সেশন তৈরি করার জন্য)...")
            await page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=60000)
            
            # অ্যান্টি-বট চেকিং পার হওয়ার জন্য এবং কুকি সেট হওয়ার জন্য অপেক্ষা
            await page.wait_for_timeout(10000)

            print("Playwright-এর মাধ্যমে সরাসরি API তে POST কল করা হচ্ছে...")
            
            # 📡 ব্রাউজারের বর্তমান সেশন ব্যবহার করে API কল
            api_response = await page.request.post(
                API_ENDPOINT,
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "Referer": TARGET_URL
                }
                # যদি API তে কোনো ডেটা পাঠানোর প্রয়োজন হয়, তবে data={"key": "value"} যুক্ত করতে পারেন
            )

            api_data = None
            if api_response.ok:
                print("✅ API রেসপন্স সফলভাবে পাওয়া গেছে!")
                api_data = await api_response.json()
            else:
                print(f"❌ API Error: স্ট্যাটাস কোড {api_response.status}")
                api_data = {"error": f"Failed with status {api_response.status}"}

            print("কুকি এক্সট্র্যাক্ট করা হচ্ছে...")
            cookies = await context.cookies()

            # ডেটা সেভ করা
            all_data = {
                "api_response": api_data,
                "cookies": cookies
            }
            
            data_file = "all_data.json"
            with open(data_file, "w") as f:
                json.dump(all_data, f, indent=4)

            msg = f"✅ <b>সফলভাবে ডেটা পাওয়া গেছে!</b>\n\n"
            msg += f"🍪 মোট কুকি: {len(cookies)}\n"
            msg += "বিস্তারিত JSON ফাইলের ভেতর দেওয়া হলো।"
            
            send_telegram_alert(msg, file_path=data_file)
            print("কাজ শেষ! ব্রাউজার বন্ধ করা হচ্ছে...")

            await browser.close()
            
    except Exception as e:
        error_msg = f"❌ স্ক্রিপ্ট রান করতে সমস্যা হয়েছে:\n<code>{str(e)}</code>"
        print(error_msg)
        send_telegram_alert(error_msg)

if __name__ == "__main__":
    asyncio.run(fetch_all_data())

