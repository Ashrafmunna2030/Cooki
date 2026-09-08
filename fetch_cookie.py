import asyncio
import json
import requests
from playwright.async_api import async_playwright

# আপনার টেলিগ্রাম বটের তথ্য
BOT_TOKEN = "8762557414:AAGvIOLarRcWKKgZWgzbXPgJdhK8akKu8rg"
CHAT_ID = "8714217646"
TARGET_URL = "https://shop.garena.my/?channel=202953"

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message}
    requests.post(url, json=payload)

def send_telegram_document(file_path):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
    with open(file_path, 'rb') as f:
        files = {'document': f}
        data = {'chat_id': CHAT_ID, 'caption': "✅ নতুন কুকি আপডেট হয়েছে (Garena Shop)!"}
        requests.post(url, data=data, files=files)

async def fetch_cookie():
    try:
        async with async_playwright() as p:
            print("ব্রাউজার লঞ্চ করা হচ্ছে...")
            
            # বিল্ট-ইন Stealth আর্গুমেন্ট ব্যবহার করা হয়েছে
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-infobars"
                ]
            )
            
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1920, "height": 1080}
            )
            
            page = await context.new_page()

            print(f"{TARGET_URL} এ ভিজিট করা হচ্ছে...")
            await page.goto(TARGET_URL, wait_until="networkidle", timeout=60000)

            # পেজ পুরোপুরি লোড হওয়ার জন্য এক্সট্রা ৫ সেকেন্ড অপেক্ষা করা
            await page.wait_for_timeout(5000)

            print("কুকি সংগ্রহ করা হচ্ছে...")
            cookies = await context.cookies()

            cookie_file = "cookies.json"
            with open(cookie_file, "w") as f:
                json.dump(cookies, f, indent=4)

            print("সফলভাবে কুকি সেভ হয়েছে!")
            
            send_telegram_document(cookie_file)

            await browser.close()
            
    except Exception as e:
        error_msg = f"❌ কুকি সংগ্রহ করতে সমস্যা হয়েছে:\n{str(e)}"
        print(error_msg)
        send_telegram_message(error_msg)

if __name__ == "__main__":
    asyncio.run(fetch_cookie())

