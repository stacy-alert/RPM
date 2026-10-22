"""Generates server-side files from GitHub secrets and FTP-uploads them —
none of this is ever committed to the (public) repo:
  - .htaccess (web-reachable topsecretproject folder): password gate + noindex header
  - .htpasswd (private, non-web-reachable folder): the hashed password
  - config.php (web-reachable, but PHP-executed so never served as text):
    the private-data path and SMTP credentials ask-about-dog.php needs

.htpasswd uses the {SHA} format (plain SHA1, base64-encoded) — one of
Apache's long-supported basic-auth hash formats, chosen because it needs
no external htpasswd binary and no extra pip package, just hashlib. If
this specific Bluehost account's Apache config rejects {SHA} for some
reason, see topsecretproject/README.md for the apr1-MD5 fallback.

Requires BLUEHOST_PRIVATE_ABSOLUTE_PATH — the real server filesystem path
to the private directory (e.g. "/home2/fzghtxmy/private_data"), which is
NOT necessarily the same string as BLUEHOST_PRIVATE_DIR (the FTP-relative
path used elsewhere to cwd there). Apache's AuthUserFile directive needs
the real filesystem path; FTP's CWD needs whatever this account's FTP
login resolves paths relative to. These must both be confirmed against
the actual account (see README) rather than assumed equal — this
account's FTP login has a history of landing somewhere other than the
account root, so treat that assumption as unverified until checked.
"""

import base64
import hashlib
import os

import ftp_sync

PUBLIC_REMOTE_DIR = os.environ["BLUEHOST_FTP_DIR"] + "/topsecretproject"
PRIVATE_REMOTE_DIR = os.environ["BLUEHOST_PRIVATE_DIR"]
PRIVATE_ABSOLUTE_PATH = os.environ["BLUEHOST_PRIVATE_ABSOLUTE_PATH"]
GATE_USERNAME = "preview"


def sha1_htpasswd_line(username: str, password: str) -> str:
    digest = hashlib.sha1(password.encode("utf-8")).digest()
    encoded = base64.b64encode(digest).decode("ascii")
    return f"{username}:{{SHA}}{encoded}"


def main():
    password = os.environ["GATE_PASSWORD"]

    htpasswd_content = sha1_htpasswd_line(GATE_USERNAME, password) + "\n"
    ftp_sync.upload_text(PRIVATE_REMOTE_DIR, ".htpasswd", htpasswd_content)

    htaccess_content = "\n".join([
        f'AuthUserFile "{PRIVATE_ABSOLUTE_PATH}/.htpasswd"',
        "AuthType Basic",
        'AuthName "Prototype — access by invitation"',
        "Require valid-user",
        "",
        'Header set X-Robots-Tag "noindex, nofollow"',
        "",
    ])
    ftp_sync.upload_text(PUBLIC_REMOTE_DIR, ".htaccess", htaccess_content)

    # config.php is server-executed, never served as raw text, so it's safe
    # to sit in the web-reachable folder — but it's still generated fresh
    # from a secret rather than committed, since the repo is public and this
    # path is otherwise undocumented infrastructure detail.
    def php_str(value: str) -> str:
        return "'" + value.replace("\\", "\\\\").replace("'", "\\'") + "'"

    config_php = "\n".join([
        "<?php",
        f"define('PRIVATE_DATA_PATH', {php_str(PRIVATE_ABSOLUTE_PATH)});",
        f"define('SMTP_HOST', {php_str(os.environ['SMTP_HOST'])});",
        f"define('SMTP_PORT', {int(os.environ['SMTP_PORT'])});",
        f"define('SMTP_USERNAME', {php_str(os.environ['SMTP_USERNAME'])});",
        f"define('SMTP_PASSWORD', {php_str(os.environ['SMTP_PASSWORD'])});",
        f"define('NOTIFY_EMAIL_TO', {php_str(os.environ['NOTIFY_EMAIL_TO'])});",
        "",
    ])
    ftp_sync.upload_text(PUBLIC_REMOTE_DIR, "config.php", config_php)

    print("Password gate and config deployed. Username:", GATE_USERNAME)


if __name__ == "__main__":
    main()
