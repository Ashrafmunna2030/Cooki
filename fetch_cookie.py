import asyncio
import json
import requests
import os
from playwright.async_api import async_playwright

# টেলিগ্রাম কনফিগারেশন
BOT_TOKEN = "8450441691:AAHrKs10fFE8TsO_7Okrjj8pn9_acanOEnc"
CHAT_ID = "-1004322570598"

# এন্ডপয়েন্ট ও টার্গেট
TARGET_URL = "https://shop.garena.my/?channel=202953"
API_ENDPOINT = "https://shop.garena.my/api/preflight"

# টার্গেটেড কুকি কি-সমূহ
WANTED_KEYS = [
    "source", "region", "language",
    "mspid2", "_fbp", "fr", "_ga",
    "datadome", "_ga_9F1KGGRJHY", "__csrf__"
]

USER_AGENT_STRING = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


def send_telegram_message(message: str):
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


def build_cookie_json(raw_cookies: list, current_id: int = 1) -> dict:
    """
    র' কুকি তালিকা থেকে প্রয়োজনীয় ফিল্ডসমূহ নিয়ে ফরম্যাটেড ডিকশনারি প্রস্তুত করা
    """
    cookie_map = {c["name"]: c["value"] for c in raw_cookies}

    result = {
        "id": current_id,
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
            print("ব্রাউজার লঞ্চ করা হচ্ছে (Headless=False)...")
            browser = await p.chromium.launch(
                headless=True,  # টেস্ট পর্যবেক্ষণ ও প্রোপার রেন্ডারিংয়ের জন্য দৃশ্যমান রাখা হয়েছে
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-infobars",
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--window-size=1920,1080"
                ]
            )

            # Client Hints, Viewport ও Locale সমন্বিত কনটেক্সট
            context = await browser.new_context(
                user_agent=USER_AGENT_STRING,
                viewport={"width": 1920, "height": 1080},
                locale="en-US",
                timezone_id="Asia/Kuala_Lumpur",
                extra_http_headers={
                    "sec-ch-ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
                    "sec-ch-ua-mobile": "?0",
                    "sec-ch-ua-platform": '"Windows"',
                    "Sec-Fetch-Dest": "document",
                    "Sec-Fetch-Mode": "navigate",
                    "Sec-Fetch-Site": "none",
                    "Sec-Fetch-User": "?1",
                    "Upgrade-Insecure-Requests": "1"
                }
            )

            page = await context.new_page()

            print(f"{TARGET_URL} এ ভিজিট করা হচ্ছে...")
            await page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(8000)

            print("সরাসরি API তে POST কল করা হচ্ছে...")
            api_response = await page.request.post(
                API_ENDPOINT,
                headers={
                    "Accept": "application/json, text/plain, */*",
                    "Content-Type": "application/json",
                    "Referer": TARGET_URL,
                    "Origin": "https://shop.garena.my",
                    "sec-ch-ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
                    "sec-ch-ua-mobile": "?0",
                    "sec-ch-ua-platform": '"Windows"'
                }
            )

            if api_response.ok:
                print("✅ API রেসপন্স সফল!")
            else:
                print(f"⚠️ API Error: স্ট্যাটাস {api_response.status}")

            print("কুকি এক্সট্র্যাক্ট করা হচ্ছে...")
            raw_cookies = await context.cookies()

            # cookie.json ম্যানেজমেন্ট (অ্যারে ফরম্যাট এবং আইডি ট্র্যাকিং)
            json_file = "cookie.json"
            existing_data = []
            next_id = 1

            if os.path.exists(json_file):
                try:
                    with open(json_file, "r", encoding="utf-8") as f:
                        content = f.read().strip()
                        if content:
                            loaded = json.loads(content)
                            if isinstance(loaded, list) and len(loaded) > 0:
                                existing_data = loaded
                                next_id = existing_data[-1].get("id", 0) + 1
                            elif isinstance(loaded, dict):
                                existing_data = [loaded]
                                next_id = loaded.get("id", 0) + 1
                except Exception as read_err:
                    print(f"JSON রিড ত্রুটি: {read_err}, নতুন তালিকা তৈরি হচ্ছে...")
                    existing_data = []

            cookie_entry = build_cookie_json(raw_cookies, current_id=next_id)
            existing_data.append(cookie_entry)

            # ফাইল সেভ
            with open(json_file, "w", encoding="utf-8") as f:
                json.dump(existing_data, f, indent=4, ensure_ascii=False)

            # টেলিগ্রামে বার্তা পাঠানো
            display_text = json.dumps(cookie_entry, indent=2, ensure_ascii=False)
            msg = (
                f"✅ <b>Cookie Updated (Educational Lab)</b>\n"
                f"🆔 <b>ID:</b> {next_id}\n"
                f"🍪 <b>Total in Pool:</b> {len(existing_data)}\n\n"
                f"<pre>{display_text}</pre>"
            )
            send_telegram_message(msg)

            print(f"সফলভাবে সংরক্ষিত! নতুন এন্ট্রি আইডি: {next_id}")
            await browser.close()

    except Exception as e:
        error_msg = f"❌ <b>স্ক্রিপ্ট এক্সিকিউশন ত্রুটি:</b>\n<code>{str(e)}</code>"
        print(error_msg)
        send_telegram_message(error_msg)


if __name__ == "__main__":
    asyncio.run(fetch_all_data())
