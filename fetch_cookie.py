import asyncio
import json
import requests
import os
import time
from datetime import datetime
from playwright.async_api import async_playwright

# ============================================================
# 🔑 CONFIG
# ============================================================
BOT_TOKEN = "8450441691:AAHrKs10fFE8TsO_7Okrjj8pn9_acanOEnc"
CHAT_ID = "-1004322570598"
FIREBASE_URL = "https://rsverify-76143-default-rtdb.firebaseio.com/cookies.json"

# ⏱️ Timing
MAX_RUNTIME = 5.5 * 3600    # 5.5 ঘণ্টা
INTERVAL = 30               # প্রতি 30 sec এ 1 cookie

# 🎯 Targets
TARGET_URL = "https://shop.garena.my/?channel=202953"
API_ENDPOINT = "https://shop.garena.my/api/preflight"

# 🔒 MASTER USER-AGENT (সব জায়গায় এটাই ব্যবহার)
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# 🎯 চাওয়া keys
WANTED_KEYS = [
    "source", "region", "language",
    "mspid2", "_fbp", "fr", "_ga",
    "datadome", "_ga_9F1KGGRJHY", "__csrf__"
]


# ============================================================
# 📤 TELEGRAM
# ============================================================
def send_telegram_message(message):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        r = requests.post(
            url,
            json={
                'chat_id': CHAT_ID,
                'text': message,
                'parse_mode': 'HTML',
                'disable_web_page_preview': True
            },
            timeout=20
        )
        return r.status_code == 200
    except Exception as e:
        print(f"Telegram alert error: {e}")
        return False


# ============================================================
# 💾 FIREBASE
# ============================================================
def save_to_firebase(cookie):
    try:
        r = requests.post(FIREBASE_URL, json=cookie, timeout=10)
        return r.status_code == 200
    except Exception as e:
        print(f"Firebase error: {e}")
        return False


# ============================================================
# 🍪 COOKIE BUILDER
# ============================================================
def build_cookie_json(raw_cookies):
    cookie_map = {c["name"]: c["value"] for c in raw_cookies}
    result = {
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


# ============================================================
# 🔥 FETCH ONE COOKIE (Master UA)
# ============================================================
async def fetch_one_cookie():
    result = None

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-infobars",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
            ]
        )

        # 🔒 Master UA — সব জায়গায় same
        context = await browser.new_context(user_agent=USER_AGENT)
        page = await context.new_page()

        try:
            print(f"🌐 Visiting: {TARGET_URL}")
            await page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(8000)

            print("📡 Calling API...")
            api_response = await page.request.post(
                API_ENDPOINT,
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "Referer": TARGET_URL,
                    "User-Agent": USER_AGENT,   # 🔒 Same Master UA
                }
            )

            if api_response.ok:
                print("✅ API success")
            else:
                print(f"⚠️ API status: {api_response.status}")

            raw_cookies = await context.cookies()
            result = build_cookie_json(raw_cookies)

        finally:
            try:
                await browser.close()
            except:
                pass

    return result


# ============================================================
# 🚀 MAIN LOOP
# ============================================================
async def main():
    print("=" * 60)
    print("🚀 fetch_cookie.py — Single Master UA")
    print(f"   Runtime: {MAX_RUNTIME/3600:.1f} hr")
    print(f"   Interval: {INTERVAL}s")
    print(f"   UA: {USER_AGENT}")
    print("=" * 60)

    send_telegram_message(
        f"🚀 <b>Cookie Worker Started</b>\n"
        f"🕐 {datetime.now():%Y-%m-%d %H:%M:%S}\n"
        f"⏱️ Runtime: {MAX_RUNTIME/3600:.1f} hr\n"
        f"⏳ Interval: {INTERVAL}s\n"
        f"🖥️ UA: Chrome/120 Windows"
    )

    start = time.time()
    count = 0
    last_log = 0
    fail_streak = 0

    while time.time() - start < MAX_RUNTIME:
        cycle = time.time()

        try:
            cookie_json = await fetch_one_cookie()

            if not cookie_json or not cookie_json.get("mspid2"):
                raise Exception("Empty cookie / no mspid2")

            json_text = json.dumps(cookie_json, indent=2, ensure_ascii=False)
            with open("cookie.json", "w", encoding="utf-8") as f:
                f.write(json_text)

            fb_ok = save_to_firebase(cookie_json)

            msg = (
                f"✅ <b>Cookie #{count+1}</b>\n"
                f"🕐 {datetime.now():%H:%M:%S}\n"
                f"🆔 <code>{cookie_json.get('mspid2','')[:20]}...</code>\n"
                f"📤 FB: {'✅' if fb_ok else '❌'}\n\n"
                f"<pre>{json_text}</pre>"
            )
            send_telegram_message(msg)

            count += 1
            fail_streak = 0
            print(f"✅ #{count} done | mspid2={cookie_json.get('mspid2','')[:12]}...")

        except Exception as e:
            fail_streak += 1
            err = f"{type(e).__name__}: {e}"
            print(f"❌ #{count+1} fail: {err}")

            if fail_streak >= 3:
                print("⚠️ 3 fails — waiting 60s...")
                send_telegram_message(f"⚠️ 3 fails:\n<code>{err[:200]}</code>")
                await asyncio.sleep(60)
                fail_streak = 0
            else:
                await asyncio.sleep(10)

        if count - last_log >= 5:
            elapsed = (time.time() - start) / 60
            rate = count / max(elapsed, 1)
            remaining = (MAX_RUNTIME - (time.time() - start)) / 3600
            print(f"📊 #{count} | {rate:.2f}/min | "
                  f"{elapsed:.0f}min elapsed | {remaining:.1f}hr left")
            last_log = count

        elapsed_cycle = time.time() - cycle
        wait = max(0, INTERVAL - elapsed_cycle)
        print(f"💤 Waiting {wait:.0f}s...")
        await asyncio.sleep(wait)

    print(f"✅ Done — {count} cookies")
    send_telegram_message(
        f"✅ <b>Worker Finished</b>\n"
        f"🍪 Total: {count} cookies\n"
        f"🕐 {datetime.now():%Y-%m-%d %H:%M:%S}"
    )


# ============================================================
# ENTRY
# ============================================================
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Stopped")
    except Exception as e:
        send_telegram_message(f"💥 Fatal: <code>{str(e)[:200]}</code>")
