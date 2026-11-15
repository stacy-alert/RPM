"""Minimal FTP/FTPS helpers for the daily workflow, using only the standard
library (ftplib) — deliberately not another black-box Action, given this
project's past experience with an FTP deploy Action producing a silently
wrong remote path. Every path used here is logged so a misconfiguration is
visible in the run output instead of silently uploading to the wrong place.

All of BLUEHOST_FTP_SERVER / USERNAME / PASSWORD are the same secrets the
main site deploy already uses. The private directory (see README) is
created automatically next to the FTP login's home folder, and its real
absolute path is discovered from the server's own PWD — never typed in or
guessed — so there's no BLUEHOST_PRIVATE_ABSOLUTE_PATH secret to keep in
sync.
"""

import io
import logging
import os
from ftplib import FTP_TLS, error_perm

log = logging.getLogger("ftp_sync")

DEFAULT_PRIVATE_DIRNAME = "topsecret_private"


def require_env(*names: str) -> None:
    """Fail loudly, naming exactly which secrets are missing, instead of
    letting a blank env var surface later as a cryptic ValueError/KeyError
    deep in some unrelated line (e.g. int('') on an unset SMTP_PORT)."""
    missing = [n for n in names if not os.environ.get(n)]
    if missing:
        raise SystemExit(
            "Missing or empty required GitHub secrets: " + ", ".join(missing) +
            ". Set these in the repo's Settings -> Secrets and variables -> "
            "Actions, then re-run."
        )


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


class PrivateDirUnsafeError(Exception):
    """Raised and never swallowed — the private directory appears to be
    inside the web root, which would make supposedly-private files
    (lookup.json, names, CAC IDs, listing URLs) publicly reachable."""


def ensure_private_dir(dirname: str | None = None) -> str:
    """Creates the private directory next to the FTP login's home folder
    if it doesn't already exist, then returns its real server absolute
    path — discovered from the FTP server's own PWD after CWD, never typed
    in or guessed, since this account's FTP login has a history of landing
    somewhere unexpected. Fails loudly (raises, does not log-and-continue)
    if that path turns out to contain "public_html" anywhere, meaning
    files meant to be private (names, CAC IDs, listing URLs) would be
    web-reachable. Runs before every upload of anything sensitive."""
    dirname = dirname or os.environ.get("BLUEHOST_PRIVATE_DIR") or DEFAULT_PRIVATE_DIRNAME
    ftps = _connect()
    try:
        log.info("FTP login home directory: %s", ftps.pwd())

        try:
            ftps.mkd(dirname)
            log.info("Created private directory: %s", dirname)
        except error_perm as e:
            log.info("mkd(%s) did not create a new directory (%s) — assuming it already exists.", dirname, e)

        ftps.cwd(dirname)
        reported_path = ftps.pwd()
        log.info("Private directory's real server path: %s", reported_path)

        if "public_html" in reported_path.lower():
            raise PrivateDirUnsafeError(
                f"REFUSING TO CONTINUE: the private directory's real server "
                f"path is '{reported_path}', which contains 'public_html'. "
                f"That means files meant to be private (names, CAC IDs, "
                f"listing URLs) would be web-reachable. This FTP account's "
                f"login home doesn't look like it has public_html as a "
                f"direct sibling — check BLUEHOST_FTP_SERVER/USERNAME."
            )

        canary_name = "_canary_write_test.txt"
        ftps.storbinary(f"STOR {canary_name}", io.BytesIO(b"safety check write test\n"))
        log.info("Canary file write to private dir succeeded: %s", canary_name)

        return reported_path
    finally:
        ftps.quit()
