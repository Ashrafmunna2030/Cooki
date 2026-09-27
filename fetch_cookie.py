"""
fetch_cookie.py — Unique Cookie Generator
- প্রতি cookie এর জন্য নতুন browser context
- সব keys (mspid2, _fbp, fr, _ga, datadome, __csrf__) unique
- Telegram + Firebase এ auto send
- 5.5 ঘণ্টা চলে, তারপর exit
"""

import asyncio
import json
import os
import time
from datetime import datetime

import requests
from playwright.async_api import async_playwright

# ============================================================
# CONFIG
# ============================================================
BOT_TOKEN = os.getenv("TG_BOT_TOKEN", "8450441691:AAHrKs10fFE8TsO_7Okrjj8pn9_acanOEnc")
CHAT_ID   = os.getenv("TG_CHAT_ID", "-1004322570598")
FIREBASE_URL = os.getenv("FIREBASE_URL", "")

TARGET_URL   = "https://shop.garena.my/?channel=202953"
API_ENDPOINT = "https://shop.garena.my/api/preflight"

# ⏱️ Timing
MAX_RUNTIME      = 5.5 * 3600   # 5.5 ঘণ্টা
INTERVAL         = 20           # প্রতি 20 sec এ 1 cookie (fresh browser slow)
RESTART_AFTER    = 5 * 3600     # 5 ঘণ্টা পর সম্পূর্ণ restart

# 🎯 চাওয়া keys
WANTED_KEYS = [
    "source", "region", "language", "mspid2",
    "_fbp", "fr", "_ga", "datadome",
    "_ga_9F1KGGRJHY", "__csrf__"
]

# 🌐 User Agents (random — unique session)
UA_POOL = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
]

# 🌏 Locale + Timezone pool
LOCALE_POOL = ["en-MY", "en-SG", "en-US", "en-GB"]
TZ_POOL     = ["Asia/Kuala_Lumpur", "Asia/Singapore", "Asia/Bangkok"]


# ============================================================
# TELEGRAM
# ============================================================
def tg_send(msg):
    if not BOT_TOKEN or not CHAT_ID:
        return False
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={
                "chat_id": CHAT_ID,
                "text": msg,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            },
            timeout=20,
        )
        return r.status_code == 200
    except Exception as e:
        print(f"TG err: {e}")
        return False


# ============================================================
# FIREBASE
# ============================================================
def save_firebase(cookie):
    if not FIREBASE_URL:
        return False
    try:
        r = requests.post(FIREBASE_URL, json=cookie, timeout=10)
        return r.status_code == 200
    except Exception as e:
        print(f"FB err: {e}")
        return False


# ============================================================
# COOKIE BUILDER
# ============================================================
def build_cookie(raw_cookies):
    cmap = {c["name"]: c["value"] for c in raw_cookies}
    result = {"source": "pc", "region": "MY", "language": "en"}
    for k in WANTED_KEYS:
        if k in ("source", "region", "language"):
            continue
        if k in cmap:
            result[k] = cmap[k]
    return result


# ============================================================
# 🔥 UNIQUE COOKIE FETCHER — প্রতিবার fresh browser
# ============================================================
async def fetch_unique_cookie(index):
    """প্রতিবার নতুন browser + context → unique cookie"""
    import random

    ua    = random.choice(UA_POOL)
    loc   = random.choice(LOCALE_POOL)
    tz    = random.choice(TZ_POOL)

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--disable-features=IsolateOrigins,site-per-process",
            ],
        )

        # 🔥 নতুন context = নতুন session (mspid2, _fbp, _ga unique)
        ctx = await browser.new_context(
            user_agent=ua,
            viewport={"width": 1366, "height": 768},
            locale=loc,
            timezone_id=tz,
            java_script_enabled=True,
            bypass_csp=True,
        )

        # Anti-detection
        await ctx.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
            Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
            window.chrome = {runtime: {}};
        """)

        page = await ctx.new_page()

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

            raw = await ctx.cookies()
            cookie = build_cookie(raw)
        finally:
            await ctx.close()
            await browser.close()

    return cookie


# ============================================================
# MAIN
# ============================================================
async def main():
    print(f"🚀 fetch_cookie.py started — max {MAX_RUNTIME/3600:.1f} hr")
    print(f"   Interval: {INTERVAL}s (unique each time)")
    tg_send(
        f"🚀 <b>fetch_cookie started</b>\n"
        f"🕐 {datetime.now():%Y-%m-%d %H:%M:%S}\n"
        f"⏱️ Runtime: {MAX_RUNTIME/3600:.1f} hr\n"
        f"🎯 Unique cookies every {INTERVAL}s"
    )

    start = time.time()
    count = 0
    last_log = 0
    fail_streak = 0

    while time.time() - start < MAX_RUNTIME:
        cycle = time.time()

        try:
            cookie = await fetch_unique_cookie(count + 1)

            # 🔒 Verificar unique
            if not cookie.get("mspid2"):
                raise Exception("Missing mspid2 — bad response")

            # Send
            jtxt = json.dumps(cookie, indent=2, ensure_ascii=False)

            fb_ok = save_firebase(cookie)
            tg_ok = tg_send(
                f"🍪 <b>Cookie #{count+1}</b>\n"
                f"🕐 {datetime.now():%H:%M:%S}\n"
                f"🆔 mspid2: <code>{cookie.get('mspid2','')[:16]}...</code>\n"
                f"📤 FB: {'✅' if fb_ok else '❌'} | TG: {'✅' if tg_ok else '❌'}\n\n"
                f"<pre>{jtxt}</pre>"
            )

            count += 1
            fail_streak = 0

        except Exception as e:
            fail_streak += 1
            print(f"❌ #{count+1} fail: {type(e).__name__}: {e}")
            # পরপর 3 বার fail হলে বেশি wait
            if fail_streak >= 3:
                print("⚠️ 3 fails — waiting 30s")
                await asyncio.sleep(30)
            else:
                await asyncio.sleep(5)

        # Log every 10 cookies
        if count - last_log >= 10:
            elapsed = (time.time() - start) / 60
            rate = count / max(elapsed, 1)
            remaining = (MAX_RUNTIME - (time.time() - start)) / 3600
            print(f"📊 #{count} | {rate:.2f}/min | {elapsed:.0f}min | "
                  f"{remaining:.1f}hr left")
            last_log = count

        # Wait for next cycle
        elapsed_cycle = time.time() - cycle
        await asyncio.sleep(max(0, INTERVAL - elapsed_cycle))

    print(f"✅ Done — {count} unique cookies")
    tg_send(
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
        print("\n👋 Stopped")
