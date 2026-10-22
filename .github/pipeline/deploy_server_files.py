"""Generates server-side files from GitHub secrets and FTP-uploads them —
none of this is ever committed to the (public) repo:
  - .htaccess (web-reachable topsecretproject folder): noindex header ONLY,
    no auth. The folder is public at its unlisted URL by design — see
    topsecretproject/README.md.
  - config.php (web-reachable, but PHP-executed so never served as text):
    the private-data path and SMTP credentials ask-about-dog.php needs

Also verifies, every run, that BLUEHOST_PRIVATE_DIR genuinely resolves
outside public_html before anything sensitive (lookup.json) is ever
uploaded there — see verify_private_dir_is_safe() in ftp_sync.py.
"""

import os

import ftp_sync

PUBLIC_REMOTE_DIR = os.environ["BLUEHOST_FTP_DIR"] + "/topsecretproject"
PRIVATE_REMOTE_DIR = os.environ["BLUEHOST_PRIVATE_DIR"]
PRIVATE_ABSOLUTE_PATH = os.environ["BLUEHOST_PRIVATE_ABSOLUTE_PATH"]


def php_str(value: str) -> str:
    return "'" + value.replace("\\", "\\\\").replace("'", "\\'") + "'"


def main():
    ftp_sync.verify_private_dir_is_safe(PRIVATE_REMOTE_DIR, PRIVATE_ABSOLUTE_PATH)

    htaccess_content = 'Header set X-Robots-Tag "noindex, nofollow"\n'
    ftp_sync.upload_text(PUBLIC_REMOTE_DIR, ".htaccess", htaccess_content)

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

    print("Server config deployed (noindex header only, no auth).")


if __name__ == "__main__":
    main()
