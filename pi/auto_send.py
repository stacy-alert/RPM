#!/usr/bin/env python3
"""Do the "Send dogs" routine automatically, once a day, on the Raspberry Pi.

Same steps as doing it by hand: open the shelter's adoptable-dogs page in a
real Chromium window, scroll to the bottom with the mouse wheel, then run the
"Send dogs" bookmark. The window lives on a virtual screen (Xvfb), so no
monitor is needed. Cincinnati Animal CARE gave the owner permission for a
once-a-day automated visit (2026-11-16).

Ground rules:
  - One visit per run. No retries in a loop.
  - If the site shows a verification challenge instead of the page, stop and
    report it. Never try to solve or get around a challenge.

Needs (one time):  sudo apt install -y xvfb chromium-browser   (or: chromium)
Also needs cac_fetch.py (with --setup done) in the same folder, for the FTP
login used to read the upload token.

Usage:
  python3 auto_send.py          # run once (what cron runs daily)
  python3 auto_send.py --check  # only check tools + token, don't visit
"""

import base64
import io
import json
import os
import shutil
import socket
import struct
import subprocess
import sys
import time
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

PAGE_URL = os.environ.get("CAC_PAGE_URL", "https://cincinnatianimalcare.org/adopt/dogs/")
COLLECT_URL = os.environ.get(
    "CAC_COLLECT_URL", "https://rpmhabitatconservation.org/topsecretproject/collect.js")
LOADED_TITLE_HINT = os.environ.get("CAC_TITLE_HINT", "adopt")
RESULT_TITLE = "Dog list upload"
DEBUG_PORT = int(os.environ.get("CAC_DEBUG_PORT", "9223"))
DISPLAY_NUM = os.environ.get("CAC_DISPLAY", ":99")
PROFILE_DIR = os.path.expanduser("~/.cac_auto_profile")
CARD_SELECTOR = '.pmp-search-result-container[data-species="dog"]'
CHALLENGE_HINTS = ("just a moment", "attention required", "verify you are human", "security check")


def log(msg):
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)


# ---------------------------------------------------------------- tools

def find_browser():
    override = os.environ.get("CAC_BROWSER")
    if override:
        return override
    for name in ("chromium-browser", "chromium"):
        path = shutil.which(name)
        if path:
            return path
    return None


def get_token():
    if os.environ.get("CAC_TOKEN"):
        return os.environ["CAC_TOKEN"]
    import cac_fetch
    from ftplib import error_perm
    env = cac_fetch.load_env()
    ftps = cac_fetch.connect(env)
    try:
        try:
            ftps.cwd(cac_fetch.PRIVATE_DIR)
        except error_perm:
            pass
        buf = io.BytesIO()
        try:
            ftps.retrbinary("RETR upload_token.txt", buf.write)
        except error_perm:
            return None
        token = buf.getvalue().decode().strip()
        return token if len(token) >= 20 else None
    finally:
        try:
            ftps.quit()
        except Exception:
            pass


# ---------------------------------------------------------------- minimal websocket (CDP)

class CDP:
    """Just enough of a websocket client to send DevTools commands."""

    def __init__(self, ws_url):
        u = urllib.parse.urlparse(ws_url)
        self.sock = socket.create_connection((u.hostname, u.port), timeout=60)
        key = base64.b64encode(os.urandom(16)).decode()
        req = (f"GET {u.path} HTTP/1.1\r\nHost: {u.hostname}:{u.port}\r\n"
               "Upgrade: websocket\r\nConnection: Upgrade\r\n"
               f"Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n")
        self.sock.sendall(req.encode())
        resp = b""
        while b"\r\n\r\n" not in resp:
            chunk = self.sock.recv(4096)
            if not chunk:
                raise ConnectionError("DevTools closed during handshake")
            resp += chunk
        if b" 101 " not in resp.split(b"\r\n", 1)[0]:
            raise ConnectionError("DevTools refused websocket: " + resp.split(b"\r\n", 1)[0].decode())
        self.buf = resp.split(b"\r\n\r\n", 1)[1]
        self.next_id = 0

    def _read(self, n):
        while len(self.buf) < n:
            chunk = self.sock.recv(65536)
            if not chunk:
                raise ConnectionError("DevTools connection closed")
            self.buf += chunk
        out, self.buf = self.buf[:n], self.buf[n:]
        return out

    def _send_frame(self, payload, opcode=1):
        mask = os.urandom(4)
        header = bytes([0x80 | opcode])
        n = len(payload)
        if n < 126:
            header += bytes([0x80 | n])
        elif n < 65536:
            header += bytes([0x80 | 126]) + struct.pack(">H", n)
        else:
            header += bytes([0x80 | 127]) + struct.pack(">Q", n)
        masked = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
        self.sock.sendall(header + mask + masked)

    def _recv_message(self):
        data = b""
        while True:
            b1, b2 = self._read(2)
            fin, opcode = b1 & 0x80, b1 & 0x0F
            n = b2 & 0x7F
            if n == 126:
                n = struct.unpack(">H", self._read(2))[0]
            elif n == 127:
                n = struct.unpack(">Q", self._read(8))[0]
            payload = self._read(n)
            if opcode == 9:          # ping -> pong
                self._send_frame(payload, opcode=10)
                continue
            if opcode == 8:
                raise ConnectionError("DevTools closed the connection")
            data += payload
            if fin:
                return data.decode("utf-8", errors="replace")

    def call(self, method, params=None, timeout=120):
        self.next_id += 1
        my_id = self.next_id
        self._send_frame(json.dumps({"id": my_id, "method": method, "params": params or {}}).encode())
        self.sock.settimeout(timeout)
        while True:
            msg = json.loads(self._recv_message())
            if msg.get("id") == my_id:
                if "error" in msg:
                    raise RuntimeError(f"{method}: {msg['error']}")
                return msg.get("result", {})

    def js(self, expression, await_promise=False, timeout=120):
        r = self.call("Runtime.evaluate", {
            "expression": expression, "returnByValue": True, "awaitPromise": await_promise,
        }, timeout=timeout)
        if "exceptionDetails" in r:
            raise RuntimeError("page script error: " + json.dumps(r["exceptionDetails"])[:400])
        return r.get("result", {}).get("value")

    def close(self):
        try:
            self._send_frame(b"", opcode=8)
            self.sock.close()
        except Exception:
            pass


def list_tabs():
    with urllib.request.urlopen(f"http://127.0.0.1:{DEBUG_PORT}/json", timeout=5) as r:
        return [t for t in json.load(r) if t.get("type") == "page"]


# ---------------------------------------------------------------- the routine

def start_virtual_screen():
    lock = f"/tmp/.X{DISPLAY_NUM.lstrip(':')}-lock"
    if os.path.exists(lock):
        log(f"Virtual screen {DISPLAY_NUM} already running; reusing it.")
        return None
    xvfb = shutil.which("Xvfb")
    proc = subprocess.Popen([xvfb, DISPLAY_NUM, "-screen", "0", "1366x900x24", "-nolisten", "tcp"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(2)
    if proc.poll() is not None:
        sys.exit("STOPPED: could not start the virtual screen (Xvfb).")
    return proc


def launch_browser(browser):
    # Clear out a browser left over from a crashed run, so the profile isn't locked.
    subprocess.run(["pkill", "-f", PROFILE_DIR], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1)
    for name in ("SingletonLock", "SingletonSocket", "SingletonCookie"):
        try:
            os.remove(os.path.join(PROFILE_DIR, name))
        except OSError:
            pass
    env = dict(os.environ, DISPLAY=DISPLAY_NUM)
    args = [browser, f"--user-data-dir={PROFILE_DIR}", "--no-first-run", "--no-default-browser-check",
            "--password-store=basic", "--disable-session-crashed-bubble",
            f"--remote-debugging-port={DEBUG_PORT}", "--window-position=0,0", "--window-size=1366,900",
            PAGE_URL]
    if os.environ.get("CAC_EXTRA_BROWSER_ARGS"):
        args[1:1] = os.environ["CAC_EXTRA_BROWSER_ARGS"].split()
    return subprocess.Popen(args, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def wait_for_page(timeout=150):
    """Poll the open tab's title until the real page loads or we give up."""
    deadline = time.time() + timeout
    last_title, saw_challenge = "", False
    while time.time() < deadline:
        try:
            tabs = list_tabs()
        except Exception:
            time.sleep(2)
            continue
        for t in tabs:
            if not t.get("url", "").startswith(PAGE_URL.split("#")[0][:30]):
                continue
            title = (t.get("title") or "").strip()
            last_title = title
            low = title.lower()
            if any(h in low for h in CHALLENGE_HINTS):
                saw_challenge = True
            elif LOADED_TITLE_HINT in low:
                return t
        time.sleep(3)
    if saw_challenge:
        sys.exit("STOPPED: the site showed a verification challenge instead of the dog page. "
                 "Not attempting to solve or bypass it. Use the Send dogs bookmark by hand today.")
    sys.exit(f"STOPPED: the dog page didn't finish loading (last title seen: {last_title!r}).")


def scroll_to_bottom(cdp):
    """Scroll with real mouse-wheel events, like a person would."""
    cdp.call("Input.dispatchMouseEvent", {"type": "mouseMoved", "x": 683, "y": 450})
    for i in range(400):
        cdp.call("Input.dispatchMouseEvent",
                 {"type": "mouseWheel", "x": 683, "y": 450, "deltaX": 0, "deltaY": 700})
        time.sleep(0.25)
        if i % 5 == 4:
            at_bottom = cdp.js("window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - 5")
            if at_bottom:
                time.sleep(3)  # let the last cards and photos settle
                return
    log("Note: stopped scrolling after 400 wheel turns without reaching the bottom.")


def run(check_only=False):
    browser = find_browser()
    missing = [n for n, ok in (("chromium", browser), ("xvfb", shutil.which("Xvfb"))) if not ok]
    if missing:
        sys.exit("Missing: " + ", ".join(missing) + ". Install with:\n"
                 "  sudo apt install -y xvfb chromium-browser\n"
                 "(if chromium-browser isn't found, use: sudo apt install -y xvfb chromium)")
    token = get_token()
    if not token:
        sys.exit("No upload token found. Run:  python3 ~/make_bookmark.py  once, then try again.")
    log(f"Tools OK ({os.path.basename(browser)}), upload token found.")
    if check_only:
        return 0

    xvfb = start_virtual_screen()
    proc = None
    cdp = None
    try:
        proc = launch_browser(browser)
        log(f"Opening {PAGE_URL}")
        tab = wait_for_page()
        log(f"Page loaded: {tab.get('title')!r}")
        cdp = CDP(tab["webSocketDebuggerUrl"])
        scroll_to_bottom(cdp)
        cards = cdp.js(f"document.querySelectorAll('{CARD_SELECTOR}').length")
        claimed = cdp.js("(document.querySelector('.pmp-search-profile-count')||{}).textContent||''")
        log(f"Scrolled to the bottom. Dog cards on the page: {cards}. Page says: {claimed.strip()!r}")

        # Same thing the Send dogs bookmark does, sent in this tab.
        cdp.js("window.__rpmDogToken = %s; window.__rpmSameTab = true;"
               "var s = document.createElement('script');"
               "s.src = %s + '?t=' + Date.now();"
               "document.body.appendChild(s); 'ok'" % (json.dumps(token), json.dumps(COLLECT_URL)))
        log("Ran the Send dogs bookmark. Waiting for the upload result...")

        deadline = time.time() + 90
        while time.time() < deadline:
            time.sleep(3)
            try:
                title = cdp.js("document.title") or ""
            except Exception:
                continue  # page is navigating
            if RESULT_TITLE.lower() in title.lower():
                time.sleep(1)
                result = (cdp.js("document.body.innerText") or "").strip()
                log("Upload page says: " + result)
                return 0 if result.startswith("Saved") else 1
            box = cdp.js("(document.getElementById('rpm-dog-box')||{}).innerText||''")
            if box:
                log("The bookmark found no dog cards. Its report:\n" + box[:3000])
                return 1
        log("STOPPED: no upload result within 90 seconds.")
        return 1
    finally:
        if cdp:
            cdp.close()
        if proc:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
        if xvfb:
            xvfb.terminate()


if __name__ == "__main__":
    sys.exit(run(check_only="--check" in sys.argv))
