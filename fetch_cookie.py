import asyncio
import json
import requests
from playwright.async_api import async_playwright

# আপনার টেলিগ্রাম বটের তথ্য
BOT_TOKEN = "8762557414:AAGvIOLarRcWKKgZWgzbXPgJdhK8akKu8rg"
CHAT_ID = "8714217646"
TARGET_URL = "https://shop.garena.my/?channel=202953"

# টেলিগ্রামে অ্যালার্ট, ছবি এবং ফাইল পাঠানোর ফাংশন
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
            
            # অ্যান্টি-বট ডিটেকশন বাইপাস করার জন্য জাভাস্ক্রিপ্ট ইনজেকশন
            await context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            """)
            
            page = await context.new_page()

            print(f"{TARGET_URL} এ ভিজিট করা হচ্ছে...")
            await page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=60000)
            
            # ক্লাউডফ্লেয়ার বা চেকিং পেজ পার হওয়ার জন্য ১০ সেকেন্ড অপেক্ষা
            await page.wait_for_timeout(10000)

            print("স্ক্রিনশট নেওয়া হচ্ছে...")
            # পেজের বর্তমান অবস্থার একটি স্ক্রিনশট নেওয়া
            await page.screenshot(path="debug_screen.png")
            send_telegram_alert("📸 সাইটের বর্তমান অবস্থার স্ক্রিনশট:", image_path="debug_screen.png")

            print("ডেটা এক্সট্রাক্ট করা হচ্ছে...")
            # ১. কুকি এক্সট্র্যাক্ট
            cookies = await context.cookies()
            
            # ২. HTML থেকে CSRF টোকেন এক্সট্র্যাক্ট
            csrf_token = await page.evaluate('''() => {
                let meta = document.querySelector('meta[name="csrf-token"], meta[name="csrf"]');
                if (meta) return meta.content;
                let input = document.querySelector('input[name="csrfmiddlewaretoken"], input[name="csrf_token"], input[name="_csrf"]');
                if (input) return input.value;
                return "Not Found in HTML";
            }''')
            
            # ৩. LocalStorage এক্সট্র্যাক্ট (অনেক সাইট এখানে সেশন টোকেন রাখে)
            local_storage = await page.evaluate("() => JSON.stringify(window.localStorage)")

            # সব ডেটা একসাথে সেভ করা
            all_data = {
                "csrf_token_html": csrf_token,
                "cookies": cookies,
                "local_storage": json.loads(local_storage) if local_storage else {}
            }
            
            data_file = "all_data.json"
            with open(data_file, "w") as f:
                json.dump(all_data, f, indent=4)

            # সামারি মেসেজ তৈরি
            msg = f"✅ <b>সফলভাবে ডেটা পাওয়া গেছে!</b>\n\n"
            msg += f"🍪 মোট কুকি: {len(cookies)}\n"
            msg += f"🔑 HTML CSRF: <code>{csrf_token}</code>\n\n"
            msg += "বাকি সব কুকি এবং LocalStorage টোকেন ফাইলের ভেতর দেওয়া হলো।"
            
            send_telegram_alert(msg, file_path=data_file)
            print("কাজ শেষ! ব্রাউজার বন্ধ করা হচ্ছে...")

            await browser.close()
            
    except Exception as e:
        error_msg = f"❌ স্ক্রিপ্ট রান করতে সমস্যা হয়েছে:\n<code>{str(e)}</code>"
        print(error_msg)
        send_telegram_alert(error_msg)

if __name__ == "__main__":
    asyncio.run(fetch_all_data())
