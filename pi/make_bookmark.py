#!/usr/bin/env python3
"""One-time: create the upload token and print the "Send dogs" bookmark.

Run on the same computer where cac_fetch.py --setup was done. It makes a
random token, stores it in the private FTP folder (where upload.php reads
it), and prints the bookmark code with that token inside. Treat the
printed bookmark like a password: anyone who has it can replace the dog
list.
"""
import io
import secrets
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cac_fetch
from ftplib import error_perm

SCRIPT_URL = "https://rpmhabitatconservation.org/topsecretproject/collect.js"

JS = """javascript:(()=>{if(location.hostname.indexOf('cincinnatianimalcare.org')<0){alert('Open the Cincinnati Animal CARE adoptable dogs page first, scroll to the bottom, then tap this.');return}window.__rpmDogToken='__TOKEN__';const s=document.createElement('script');s.src='__URL__?t='+Date.now();s.onerror=()=>alert('Send dogs: could not load the helper script. Tell Claude: script blocked.');document.body.appendChild(s)})();"""


def main():
    env = cac_fetch.load_env()
    token = secrets.token_urlsafe(32)
    ftps = cac_fetch.connect(env)
    try:
        try:
            ftps.cwd(cac_fetch.PRIVATE_DIR)
        except error_perm:
            pass
        where = ftps.pwd()
        if "public_html" in where.lower():
            sys.exit(f"REFUSING: '{where}' is inside the public web folder.")
        # Keep the existing token if there is one, so an older bookmark
        # keeps working.
        buf = io.BytesIO()
        try:
            ftps.retrbinary("RETR upload_token.txt", buf.write)
            existing = buf.getvalue().decode().strip()
        except error_perm:
            existing = ""
        if len(existing) >= 20 and "--new" not in sys.argv:
            token = existing
        else:
            ftps.storbinary("STOR upload_token.txt", io.BytesIO(token.encode()))
    finally:
        ftps.quit()
    print("Token saved to the private folder.\n")
    print("Copy EVERYTHING between the lines below. That is your bookmark:\n")
    print("-" * 60)
    print(JS.replace("__URL__", SCRIPT_URL).replace("__TOKEN__", token))
    print("-" * 60)


if __name__ == "__main__":
    main()
