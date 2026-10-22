"""Minimal FTP/FTPS helpers for the daily workflow, using only the standard
library (ftplib) — deliberately not another black-box Action, given this
project's past experience with an FTP deploy Action producing a silently
wrong remote path. Every path used here is logged so a misconfiguration is
visible in the run output instead of silently uploading to the wrong place.

All of BLUEHOST_FTP_SERVER / USERNAME / PASSWORD are the same secrets the
main site deploy already uses. BLUEHOST_PRIVATE_DIR is new (see README) —
an explicit, owner-confirmed absolute-or-account-relative path OUTSIDE
public_html, never guessed from a relative "..".
"""

import io
import logging
import os
from ftplib import FTP_TLS

log = logging.getLogger("ftp_sync")


def _connect() -> FTP_TLS:
    server = os.environ["BLUEHOST_FTP_SERVER"]
    username = os.environ["BLUEHOST_FTP_USERNAME"]
    password = os.environ["BLUEHOST_FTP_PASSWORD"]
    ftps = FTP_TLS(server)
    ftps.login(username, password)
    ftps.prot_p()
    return ftps


def _cwd_logged(ftps: FTP_TLS, path: str):
    log.info("CWD to: %s", path)
    ftps.cwd(path)
    log.info("Now in (server-reported): %s", ftps.pwd())


def download_text(remote_dir: str, filename: str) -> str | None:
    """Download a text file; return None if it doesn't exist yet (first run)."""
    ftps = _connect()
    try:
        _cwd_logged(ftps, remote_dir)
        buf = io.BytesIO()
        ftps.retrbinary(f"RETR {filename}", buf.write)
        return buf.getvalue().decode("utf-8")
    except Exception as e:
        log.info("Could not download %s/%s (%s) — treating as first run.", remote_dir, filename, e)
        return None
    finally:
        ftps.quit()


def upload_text(remote_dir: str, filename: str, content: str):
    ftps = _connect()
    try:
        _cwd_logged(ftps, remote_dir)
        ftps.storbinary(f"STOR {filename}", io.BytesIO(content.encode("utf-8")))
        log.info("Uploaded %s to %s", filename, remote_dir)
    finally:
        ftps.quit()
