#!/usr/bin/env python3
import asyncio, json, requests, os, time
from playwright.async_api import async_playwright

BOT_TOKEN = "8450441691:AAHrKs10fFE8TsO_7Okrjj8pn9_acanOEnc"
CHAT_ID   = "-1004322570598"

TARGET_URL   = "https://shop.garena.my/?channel=202953"
API_ENDPOINT = "https://shop.garena.my/api/preflight"

UA = ("Mozilla/5.0 (Linux; Android 12; M2101K7AI Build/SKQ1.210908.001) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.8010.36 Mobile Safari/537.36")

BASE_HEADERS = {
    "sec-ch-ua-platform": '"Android"',
    "sec-ch-ua": '"Android WebView";v="153", "Not_A Brand";v="8", "Chromium";v="153"',
    "sec-ch-ua-mobile": "?1",
    "X-Requested-With": "mark.via.gp",
    "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8",
}

WANTED_KEYS = [
    "mspid2", "_fbp", "fr", "_ga",
    "datadome", "_ga_9F1KGGRJHY", "__csrf__", "csrf", "session_key"
]

ALL_DATA_FILE = "all_data.json"


def send_telegram_message(message):
    try:
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={"chat_id": CHAT_ID, "text": message,
                  "parse_mode": "HTML", "disable_web_page_preview": True},
            timeout=20,
        )
    except Exception as e:
        print(f"Telegram alert error: {e}")


def build_cookie_json(raw_cookies):
    cmap = {c["name"]: c["value"] for c in raw_cookies}
    result = {"source": "mb", "region": "BD", "language": "en"}
    for key in WANTED_KEYS:
        if key in cmap:
            result[key] = cmap[key]
    if "__csrf__" in result and "csrf" not in result:
        result["csrf"] = result["__csrf__"]
    return result


async def fetch_all_data():
    try:
        async with async_playwright() as p:
            print("🚀 Launching browser (Mobile UA)...")
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-infobars", "--no-sandbox",
                    "--disable-dev-shm-usage", "--disable-gpu",
                    "--no-first-run", "--no-default-browser-check",
                ]
            )
            context = await browser.new_context(
                user_agent=UA,
                viewport={"width": 412, "height": 915},
                device_scale_factor=2.625,
                is_mobile=True, has_touch=True,
                locale="en-GB", timezone_id="Asia/Dhaka",
                extra_http_headers=BASE_HEADERS,
            )
            page = await context.new_page()

            print(f"🌐 Visiting {TARGET_URL}")
            await page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(10000)

            print("📡 Calling /api/preflight...")
            try:
                api_response = await page.request.post(
                    API_ENDPOINT,
                    headers={
                        "Accept": "application/json",
                        "Content-Type": "application/json",
                        "Referer": TARGET_URL,
                        "Origin": "https://shop.garena.my",
                    }
                )
                print("✅ API OK" if api_response.ok
                      else f"⚠️ API status {api_response.status}")
            except Exception as e:
                print(f"⚠️ Preflight failed: {e}")

            print("🍪 Extracting cookies...")
            raw_cookies = await context.cookies()
            cookie_json = build_cookie_json(raw_cookies)

            # ---------- SAVE to all_data.json ----------
            all_data = {
                "ts": int(time.time()),
                "fetched_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "count": len(cookie_json),
                "cookies": cookie_json,
            }
            with open(ALL_DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(all_data, f, indent=2, ensure_ascii=False)

            print(f"✅ Cookies fetched: {len(cookie_json)} keys")
            print(f"✅ Saved → {ALL_DATA_FILE}")

            # ---------- Telegram ----------
            compact = json.dumps(cookie_json, separators=(",", ":"))
            msg = (
                f"🍪 <b>COOKIE_UPDATE</b>\n"
                f"🕒 {all_data['fetched_at']}\n"
                f"🔑 {len(cookie_json)} keys\n"
                f"<code>{compact}</code>"
            )
            send_telegram_message(msg)

            print("🔒 Closing browser...")
            await browser.close()
            return cookie_json

    except Exception as e:
        err = f"❌ <b>Script Error:</b>\n<code>{str(e)}</code>"
        print(err)
        send_telegram_message(err)
        return None


if __name__ == "__main__":
    result = asyncio.run(fetch_all_data())
    if result:
        print("\n" + "=" * 70)
        print("COOKIE JSON:")
        print("=" * 70)
        print(json.dumps(result, indent=2, ensure_ascii=False))
