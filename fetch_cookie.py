import asyncio
import json
import requests
from playwright.async_api import async_playwright

BOT_TOKEN = "8762557414:AAGvIOLarRcWKKgZWgzbXPgJdhK8akKu8rg"
CHAT_ID = "8714217646"
TARGET_URL = "https://shop.garena.my/?channel=202953"

def send_telegram_alert(message, file_path=None, image_path=None):
    try:
        if image_path:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
            with open(image_path, 'rb') as f:
                requests.post(url, data={'chat_id': CHAT_ID, 'caption': message}, files={'photo': f})
        elif file_path:
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
                    "--disable-infobars",
                    "--window-size=1920,1080",
                    "--no-sandbox"
                ]
            )
            
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1920, "height": 1080}
            )
            
            await context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            """)
            
            page = await context.new_page()

            # -----------------------------------------------------
            # 📡 API Network Listener (CSRF ধরার জন্য)
            # -----------------------------------------------------
            api_csrf_data = None

            async def handle_response(response):
                nonlocal api_csrf_data
                # যদি রিকোয়েস্ট URL-এ preflight থাকে এবং সেটি POST রিকোয়েস্ট হয়
                if "api/preflight" in response.url and response.request.method == "POST":
                    try:
                        print("📡 Preflight API রিকোয়েস্ট ধরা পড়েছে!")
                        api_csrf_data = await response.json()
                    except Exception as e:
                        print(f"API থেকে JSON পার্স করতে সমস্যা: {e}")

            # পেজ লোড হওয়ার আগেই লিসেনার চালু করে দেওয়া হলো
            page.on("response", handle_response)
            # -----------------------------------------------------

            print(f"{TARGET_URL} এ ভিজিট করা হচ্ছে...")
            await page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=60000)
            
            # API রেসপন্স আসার জন্য একটু সময় দেওয়া হলো
            await page.wait_for_timeout(10000)

            print("ডেটা এক্সট্রাক্ট করা হচ্ছে...")
            cookies = await context.cookies()
            local_storage = await page.evaluate("() => JSON.stringify(window.localStorage)")

            # সব ডেটা একসাথে সেভ করা
            all_data = {
                "api_preflight_response": api_csrf_data if api_csrf_data else "API Response Not Caught",
                "cookies": cookies,
                "local_storage": json.loads(local_storage) if local_storage else {}
            }
            
            data_file = "all_data.json"
            with open(data_file, "w") as f:
                json.dump(all_data, f, indent=4)

            msg = f"✅ <b>সফলভাবে ডেটা পাওয়া গেছে!</b>\n\n"
            msg += f"🍪 মোট কুকি: {len(cookies)}\n"
            if api_csrf_data:
                msg += f"🎯 <b>Preflight API থেকে ডেটা পাওয়া গেছে!</b>\n\n"
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
