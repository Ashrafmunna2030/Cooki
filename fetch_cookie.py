"""
fetch_cookie.py — Final Version
- Bot Token + Chat ID hardcoded
- Firebase + Telegram auto send
- 5.5 ঘণ্টা loop, প্রতি 20 sec
"""

import asyncio
import json
import os
import time
from datetime import datetime

import requests
from playwright.async_api import async_playwright

# ============================================================
# 🔑 CONFIG (Bot Token + Chat ID + Firebase)
# ============================================================
BOT_TOKEN    = "8450441691:AAHrKs10fFE8TsO_7Okrjj8pn9_acanOEnc"
CHAT_ID      = "-1004322570598"
FIREBASE_URL = "https://rsverify-76143-default-rtdb.firebaseio.com/cookies.json"

# ============================================================
# ⚙️ TIMING
# ============================================================
MAX_RUNTIME = 5.5 * 3600   # 5.5 ঘণ্টা
INTERVAL    = 20           # প্রতি 20 sec এ 1 cookie

# ============================================================
# 🎯 TARGETS
# ============================================================
TARGET_URL   = "https://shop.garena.my/?channel=202953"
API_ENDPOINT = "https://shop.garena.my/api/preflight"

WANTED_KEYS = [
    "source", "region", "language", "mspid2",
    "_fbp", "fr", "_ga", "datadome",
    "_ga_9F1KGGRJHY", "__csrf__"
]

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


# ============================================================
# 📤 TELEGRAM
# ============================================================
def send_telegram_message(message):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        r = requests.post(
            url,
            json={
                "chat_id": CHAT_ID,
                "text": message,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            },
            timeout=20,
        )
        return r.status_code == 200
    except Exception as e:
        print(f"Telegram alert error: {e}")
        return False


# ============================================================
# 💾 FIREBASE
# ============================================================
def save_to_firebase(cookie):
    if not FIREBASE_URL:
        return False
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
    result = {"source": "pc", "region": "MY", "language": "en"}
    for key in WANTED_KEYS:
        if key in ("source", "region", "language"):
            continue
        if key in cookie_map:
            result[key] = cookie_map[key]
    return result


# ============================================================
# 🔥 SINGLE COOKIE FETCH
# ============================================================
async def fetch_one_cookie():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-infobars",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
            ],
        )

        context = await browser.new_context(user_agent=USER_AGENT)
        page = await context.new_page()

        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            window.chrome = { runtime: {} };
        """)

        cookie_json = None

        try:
            await page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(3500)

            try:
                await page.request.post(
                    API_ENDPOINT,
                    headers={
                        "Accept": "application/json",
                        "Content-Type": "application/json",
                        "Referer": TARGET_URL,
                        "Origin": "https://shop.garena.my",
                    },
                )
            except Exception:
                pass

            raw = await context.cookies()
            cookie_json = build_cookie_json(raw)

            # Local backup
            with open("cookie.json", "w", encoding="utf-8") as f:
                f.write(json.dumps(cookie_json, indent=2, ensure_ascii=False))

        finally:
            try:
                await context.close()
            except:
                pass
            try:
                await browser.close()
            except:
                pass

    return cookie_json


# ============================================================
# 🚀 MAIN
# ============================================================
async def main():
    print("=" * 60)
    print("🚀 fetch_cookie.py started")
    print(f"   Runtime : {MAX_RUNTIME/3600:.1f} hr")
    print(f"   Interval: {INTERVAL}s")
    print(f"   Bot     : {BOT_TOKEN[:20]}...")
    print(f"   Chat    : {CHAT_ID}")
    print(f"   FB URL  : {FIREBASE_URL[:70]}")
    print("=" * 60)

    started = send_telegram_message(
        f"🚀 <b>fetch_cookie started</b>\n"
        f"🕐 {datetime.now():%Y-%m-%d %H:%M:%S}\n"
        f"⏱️ {MAX_RUNTIME/3600:.1f} hr runtime\n"
        f"🎯 Every {INTERVAL}s"
    )
    print(f"📤 Startup TG: {'✅' if started else '❌'}")

    start = time.time()
    count = 0
    last_log = 0
    fail_streak = 0

    while time.time() - start < MAX_RUNTIME:
        cycle_start = time.time()

        try:
            cookie = await fetch_one_cookie()

            if not cookie or not cookie.get("mspid2"):
                raise Exception("Empty cookie / no mspid2")

            fb_ok = save_to_firebase(cookie)

            jtxt = json.dumps(cookie, indent=2, ensure_ascii=False)
            send_telegram_message(
                f"🍪 <b>Cookie #{count+1}</b>\n"
                f"🕐 {datetime.now():%H:%M:%S}\n"
                f"🆔 <code>{cookie.get('mspid2','')[:20]}...</code>\n"
                f"📤 FB: {'✅' if fb_ok else '❌'}\n\n"
                f"<pre>{jtxt}</pre>"
            )

            count += 1
            fail_streak = 0
            print(f"✅ #{count} | mspid2={cookie.get('mspid2','')[:12]}...")

        except Exception as e:
            fail_streak += 1
            print(f"❌ #{count+1} fail: {type(e).__name__}: {e}")

            if fail_streak >= 3:
                print("⚠️ 3 fails — waiting 30s")
                await asyncio.sleep(30)
                fail_streak = 0
            else:
                await asyncio.sleep(5)

        if count - last_log >= 10:
            elapsed = (time.time() - start) / 60
            rate = count / max(elapsed, 1)
            remaining = (MAX_RUNTIME - (time.time() - start)) / 3600
            print(f"📊 #{count} | {rate:.2f}/min | "
                  f"{elapsed:.0f}min | {remaining:.1f}hr left")
            last_log = count

        elapsed_cycle = time.time() - cycle_start
        wait = max(0, INTERVAL - elapsed_cycle)
        await asyncio.sleep(wait)

    print(f"✅ Done — {count} cookies")
    send_telegram_message(
        f"✅ <b>fetch_cookie finished</b>\n"
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
        print("\n👋 Stopped manually")
    except Exception as e:
        print(f"\n💥 Fatal: {e}")
        send_telegram_message(f"💥 <b>Fatal error</b>\n<code>{str(e)[:200]}</code>")
