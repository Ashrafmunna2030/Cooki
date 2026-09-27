"""
FF Cookie Worker — 6 Hour Version
- Browser একবার খুলে ~5.5 ঘণ্টা চালায়
- প্রতি INTERVAL সেকেন্ডে cookie → Telegram
- প্রতি 30 min এ browser restart
- Job শেষে (5.5 hr) exit → GitHub Actions chain
"""

import asyncio
import json
import requests
import os
import time
from datetime import datetime
from playwright.async_api import async_playwright

# ============================================================
# CONFIG
# ============================================================
BOT_TOKEN = "8450441691:AAHrKs10fFE8TsO_7Okrjj8pn9_acanOEnc"
CHAT_ID   = "-1004322570598"

TARGET_URL   = "https://shop.garena.my/?channel=202953"
API_ENDPOINT = "https://shop.garena.my/api/preflight"

# 🔥 Timing
MAX_RUNTIME      = 5.5 * 3600    # 5.5 ঘণ্টা (30 min buffer for 6 hr limit)
INTERVAL         = 15            # প্রতি 15 sec এ 1 cookie = 4/min
BROWSER_RESTART  = 1800          # প্রতি 30 min এ browser restart
WAIT_AFTER_LOAD  = 3             # page load এর পর wait (sec)

# 🎯 চাওয়া cookie keys
WANTED_KEYS = [
    "source", "region", "language",
    "mspid2", "_fbp", "fr", "_ga",
    "datadome", "_ga_9F1KGGRJHY", "__csrf__"
]

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
      "AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/120.0.0.0 Safari/537.36")


# ============================================================
# TELEGRAM
# ============================================================
def send_telegram_message(message):
    """Telegram এ message পাঠাও (retry সহ)"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    for attempt in range(3):
        try:
            r = requests.post(url, json=payload, timeout=20)
            if r.status_code == 200:
                return True
            if r.status_code == 429:
                wait = r.json().get("parameters", {}).get("retry_after", 30)
                print(f"⚠️ TG flood — waiting {wait}s")
                time.sleep(wait)
                continue
            print(f"⚠️ TG status {r.status_code}: {r.text[:100]}")
            return False
        except Exception as e:
            print(f"❌ TG error: {e}")
            time.sleep(2)
    return False


# ============================================================
# COOKIE BUILDER
# ============================================================
def build_cookie_json(raw_cookies):
    """Playwright cookies → clean dict"""
    cmap = {c["name"]: c["value"] for c in raw_cookies}
    result = {"source": "pc", "region": "MY", "language": "en"}
    for key in WANTED_KEYS:
        if key in ("source", "region", "language"):
            continue
        if key in cmap:
            result[key] = cmap[key]
    return result


# ============================================================
# BROWSER SESSION
# ============================================================
class CookieSession:
    def __init__(self):
        self.pw = None
        self.browser = None
        self.ctx = None
        self.page = None
        self.started_at = 0

    async def start(self):
        await self.close()
        self.pw = await async_playwright().start()
        self.browser = await self.pw.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-infobars",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
            ]
        )
        self.ctx = await self.browser.new_context(user_agent=UA)
        self.page = await self.ctx.new_page()
        self.started_at = time.time()
        print(f"[{datetime.now():%H:%M:%S}] 🌐 Browser started")

    async def close(self):
        try:
            if self.browser:
                await self.browser.close()
        except Exception:
            pass
        try:
            if self.pw:
                await self.pw.stop()
        except Exception:
            pass
        self.browser = self.ctx = self.page = None

    def age(self):
        return time.time() - self.started_at

    async def fetch_cookie(self):
        # First time vs reload
        if not self.page.url or self.page.url == "about:blank":
            await self.page.goto(TARGET_URL,
                                 wait_until="domcontentloaded",
                                 timeout=60000)
        else:
            try:
                await self.page.reload(wait_until="domcontentloaded",
                                       timeout=60000)
            except Exception:
                await self.page.goto(TARGET_URL,
                                     wait_until="domcontentloaded",
                                     timeout=60000)

        await self.page.wait_for_timeout(WAIT_AFTER_LOAD * 1000)

        # API hit (session warm)
        try:
            await self.page.request.post(
                API_ENDPOINT,
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "Referer": TARGET_URL,
                },
            )
        except Exception:
            pass

        raw = await self.ctx.cookies()
        return build_cookie_json(raw)


# ============================================================
# MAIN WORKER
# ============================================================
async def run_worker():
    print(f"🚀 Worker started — max {MAX_RUNTIME/3600:.1f} hr, "
          f"interval {INTERVAL}s")

    send_telegram_message(
        f"🚀 <b>Worker Started</b>\n"
        f"⏱️ Runtime: {MAX_RUNTIME/3600:.1f} hr\n"
        f"🔄 Interval: {INTERVAL}s\n"
        f"🕐 {datetime.now():%Y-%m-%d %H:%M:%S}"
    )

    session = CookieSession()
    await session.start()

    start = time.time()
    count = 0
    last_log = 0

    while time.time() - start < MAX_RUNTIME:
        cycle = time.time()

        # Browser restart if old
        if session.age() > BROWSER_RESTART:
            print(f"[{datetime.now():%H:%M:%S}] ♻️ Restarting browser...")
            try:
                await session.start()
            except Exception as e:
                print(f"❌ Restart failed: {e}")
                await asyncio.sleep(10)
                continue

        # Fetch cookie
        try:
            cookie = await session.fetch_cookie()
            json_text = json.dumps(cookie, indent=2, ensure_ascii=False)

            # Local backup
            with open("cookie.json", "w", encoding="utf-8") as f:
                f.write(json_text)

            # Telegram send
            msg = (
                f"🍪 <b>Cookie #{count+1}</b>\n"
                f"🕐 {datetime.now():%H:%M:%S}\n"
                f"🔑 {len(cookie)} keys\n\n"
                f"<pre>{json_text}</pre>"
            )
            send_telegram_message(msg)
            count += 1

        except Exception as e:
            print(f"[{datetime.now():%H:%M:%S}] ❌ {type(e).__name__}: {e}")
            try:
                await session.start()
            except Exception as e2:
                print(f"❌ Restart failed: {e2}")
                await asyncio.sleep(10)

        # Log every 20 cookies
        if count - last_log >= 20:
            elapsed = (time.time() - start) / 60
            rate = count / max(elapsed, 1)
            remaining = (MAX_RUNTIME - (time.time() - start)) / 3600
            print(f"[{datetime.now():%H:%M:%S}] 📊 #{count} "
                  f"({rate:.1f}/min, {elapsed:.0f} min, "
                  f"{remaining:.1f} hr left)")
            last_log = count

        # Sleep to maintain interval
        elapsed_cycle = time.time() - cycle
        await asyncio.sleep(max(0, INTERVAL - elapsed_cycle))

    # Done
    print(f"✅ Done — {count} cookies in {MAX_RUNTIME/3600:.1f} hr")
    send_telegram_message(
        f"✅ <b>Worker Finished</b>\n"
        f"🍪 Total: {count} cookies\n"
        f"🕐 {datetime.now():%Y-%m-%d %H:%M:%S}"
    )
    await session.close()


# ============================================================
# ENTRY
# ============================================================
if __name__ == "__main__":
    try:
        asyncio.run(run_worker())
    except KeyboardInterrupt:
        print("\n👋 Stopped manually")
