#!/usr/bin/env python3
"""Fetch Cincinnati Animal CARE's public adoptable-dog list and upload it.

Runs on a Raspberry Pi (or any home computer). Standard library only --
nothing to pip install. It does the one thing GitHub's servers get
refused for: reading the shelter's public listing page. Everything else
(photo download, breed classification, publishing) stays in the GitHub
workflow, which picks up the file this script uploads.

Usage:
  python3 cac_fetch.py --setup   # one time: saves the FTP login to ~/.cac_fetch.env
  python3 cac_fetch.py           # fetch + upload (what cron runs daily)

Ground rules (same as .github/pipeline/scraper.py):
  - One request per run, honest User-Agent naming the project.
  - If the site answers with anything that looks like a block, log it
    and exit. No retries, no header changes, no workarounds.
"""

import getpass
import io
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from ftplib import FTP_TLS, error_perm
from html.parser import HTMLParser

LISTING_URL = "https://cincinnatianimalcare.org/adopt/dogs/"
USER_AGENT = "RPM Shelter Breed Preview (prototype, non-commercial)"
ENV_PATH = os.path.expanduser("~/.cac_fetch.env")
PRIVATE_DIR = "topsecret_private"
REMOTE_FILENAME = "cac_raw.json"
SIZE_DISPLAY = {"s": "Small", "m": "Medium", "l": "Large", "xl": "Extra Large"}
BLOCK_MARKERS = ("captcha", "access denied", "checking your browser")


def log(msg):
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)


class ListingParser(HTMLParser):
    """Reads each dog card's data-* attributes (PetMatchPro markup)."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.dogs = []
        self.claimed_total = None
        self._current = None
        self._in_count = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        classes = (a.get("class") or "").split()
        if "pmp-search-profile-count" in classes:
            self._in_count = True
        if "pmp-search-result-container" in classes:
            self._current = self._card(a)
            if self._current:
                self.dogs.append(self._current)
        elif "pmp-search-result-name-link" in classes and self._current is not None:
            if not self._current.get("listing_url"):
                self._current["listing_url"] = a.get("href")

    def handle_data(self, data):
        if self._in_count:
            m = re.search(r"(\d+)", data)
            if m:
                self.claimed_total = int(m.group(1))
                self._in_count = False

    @staticmethod
    def _card(a):
        if a.get("data-species") != "dog" or a.get("data-status") != "available":
            return None
        cac_id = a.get("data-id") or a.get("data-animal-id")
        if not cac_id:
            return None
        photos = []
        for key in ("data-photourl", "data-photourl1", "data-photourl2",
                    "data-photourl3", "data-photourl4"):
            url = a.get(key)
            if url and url not in photos:
                photos.append(url)
        size_code = a.get("data-afsize")
        age = a.get("data-afage")
        sex = a.get("data-gender")
        return {
            "cac_id": cac_id,
            "shelter_seq_id": a.get("data-seqid"),
            "name": a.get("data-animal-name") or a.get("data-name"),
            "listing_url": None,
            "photo_urls": photos,
            "sex": sex.capitalize() if sex else None,
            "age": age.capitalize() if age else None,
            "size": SIZE_DISPLAY.get(size_code, size_code),
            "date_listed": a.get("data-intakedate"),
        }


def fetch_listing():
    req = urllib.request.Request(LISTING_URL, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            status = resp.status
            html = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        sys.exit(f"STOPPED: the shelter's site answered HTTP {e.code}. "
                 "Looks like a block. Not retrying or working around it.")
    except urllib.error.URLError as e:
        sys.exit(f"STOPPED: could not reach the shelter's site ({e.reason}).")
    if status in (403, 429, 503) or any(m in html[:5000].lower() for m in BLOCK_MARKERS):
        sys.exit(f"STOPPED: response looks like a block (HTTP {status}). "
                 "Not retrying or working around it.")
    return html


def load_env():
    if not os.path.exists(ENV_PATH):
        sys.exit(f"No FTP login saved yet. Run:  python3 {os.path.abspath(__file__)} --setup")
    env = {}
    with open(ENV_PATH) as f:
        for line in f:
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.rstrip("\n").split("=", 1)
                env[k.strip()] = v
    for key in ("FTP_SERVER", "FTP_USERNAME", "FTP_PASSWORD"):
        if not env.get(key):
            sys.exit(f"{ENV_PATH} is missing {key}. Re-run with --setup.")
    return env


def setup():
    print("One-time setup. These are the same Bluehost FTP details your website deploy uses.")
    server = input("FTP server (e.g. ftp.rpmhabitatconservation.org): ").strip()
    username = input("FTP username: ").strip()
    password = getpass.getpass("FTP password (hidden as you type): ")
    fd = os.open(ENV_PATH, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write(f"FTP_SERVER={server}\nFTP_USERNAME={username}\nFTP_PASSWORD={password}\n")
    os.chmod(ENV_PATH, 0o600)
    print(f"Saved to {ENV_PATH} (readable only by you). Testing the login...")
    ftps = connect(load_env())
    print(f"Login OK. Server says we are in: {ftps.pwd()}")
    ftps.quit()


def connect(env):
    ftps = FTP_TLS(env["FTP_SERVER"], timeout=60)
    ftps.login(env["FTP_USERNAME"], env["FTP_PASSWORD"])
    ftps.prot_p()
    return ftps


def upload(env, payload):
    ftps = connect(env)
    try:
        # Two kinds of login work: the main account (opens in the home
        # folder, so step into the private folder), or a dedicated FTP
        # account whose own folder IS the private folder (already there).
        try:
            ftps.cwd(PRIVATE_DIR)
        except error_perm:
            pass
        where = ftps.pwd()
        if "public_html" in where.lower():
            sys.exit(f"REFUSING to upload: '{where}' is inside the public web folder.")
        ftps.storbinary(f"STOR {REMOTE_FILENAME}", io.BytesIO(payload.encode("utf-8")))
        log(f"Uploaded {REMOTE_FILENAME} to {where}")
    finally:
        try:
            ftps.quit()
        except Exception:
            pass


def main():
    if "--setup" in sys.argv:
        setup()
        return
    env = load_env()
    log(f"Fetching {LISTING_URL}")
    html = fetch_listing()
    parser = ListingParser()
    parser.feed(html)
    dogs = parser.dogs
    log(f"Found {len(dogs)} dog(s). Page claims: {parser.claimed_total}")
    if not dogs:
        sys.exit("STOPPED: found 0 dogs, so nothing was uploaded "
                 "(page layout may have changed, or the list loads differently).")
    if parser.claimed_total and len(dogs) < parser.claimed_total:
        log(f"NOTE: {parser.claimed_total - len(dogs)} fewer than the page claims; "
            "the rest probably load as you scroll.")
    payload = json.dumps({
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "claimed_total": parser.claimed_total,
        "dogs": dogs,
    })
    upload(env, payload)
    log("Done. The GitHub workflow will pick this up on its next run.")


if __name__ == "__main__":
    main()
