"""Generates server-side files from GitHub secrets and FTP-uploads them —
none of this is ever committed to the (public) repo:
  - .htaccess (web-reachable topsecretproject folder): noindex header ONLY,
    no auth. The folder is public at its unlisted URL by design — see
    topsecretproject/README.md.
  - config.php (web-reachable, but PHP-executed so never served as text):
    the private-data path and SMTP credentials ask-about-dog.php needs

Also creates the private directory if it doesn't exist yet and verifies,
every run, that it genuinely resolves outside public_html before anything
sensitive (lookup.json) is ever uploaded there — see ensure_private_dir()
in ftp_sync.py. Its absolute path is discovered from the FTP server
itself, not supplied as a secret.

SMTP_HOST/SMTP_PORT default to this site's own Bluehost mailbox over
implicit TLS on port 465 (Bluehost's own documented SMTP settings) unless
overridden — see README for why port 465 needs SMTPS, not STARTTLS.
"""

import os

import ftp_sync

ftp_sync.require_env(
    "BLUEHOST_FTP_SERVER", "BLUEHOST_FTP_USERNAME", "BLUEHOST_FTP_PASSWORD", "BLUEHOST_FTP_DIR",
)

PUBLIC_REMOTE_DIR = os.environ["BLUEHOST_FTP_DIR"] + "/topsecretproject"
SMTP_HOST = os.environ.get("SMTP_HOST") or "rpmhabitatconservation.org"
SMTP_PORT = int(os.environ.get("SMTP_PORT") or "465")
MAIL_CONFIGURED = bool(
    os.environ.get("SMTP_USERNAME") and os.environ.get("SMTP_PASSWORD") and os.environ.get("NOTIFY_EMAIL_TO")
)


def php_str(value: str) -> str:
    return "'" + value.replace("\\", "\\\\").replace("'", "\\'") + "'"


def main():
    private_absolute_path = ftp_sync.ensure_private_dir()

    htaccess_content = 'Header set X-Robots-Tag "noindex, nofollow"\n'
    ftp_sync.upload_text(PUBLIC_REMOTE_DIR, ".htaccess", htaccess_content)

    config_lines = [
        "<?php",
        f"define('PRIVATE_DATA_PATH', {php_str(private_absolute_path)});",
        f"define('MAIL_CONFIGURED', {'true' if MAIL_CONFIGURED else 'false'});",
    ]
    if MAIL_CONFIGURED:
        config_lines += [
            f"define('SMTP_HOST', {php_str(SMTP_HOST)});",
            f"define('SMTP_PORT', {SMTP_PORT});",
            f"define('SMTP_USERNAME', {php_str(os.environ['SMTP_USERNAME'])});",
            f"define('SMTP_PASSWORD', {php_str(os.environ['SMTP_PASSWORD'])});",
            f"define('NOTIFY_EMAIL_TO', {php_str(os.environ['NOTIFY_EMAIL_TO'])});",
        ]
    config_lines.append("")
    ftp_sync.upload_text(PUBLIC_REMOTE_DIR, "config.php", "\n".join(config_lines))

    if MAIL_CONFIGURED:
        print("Server config deployed (noindex header only, no auth). Email inquiries: configured.")
    else:
        print(
            "Server config deployed (noindex header only, no auth). Email inquiries: "
            "NOT configured (BLUEHOST_SMTP_USERNAME/PASSWORD/NOTIFY_EMAIL_TO not set) -- "
            "skipping; the dog list still deploys fine."
        )


if __name__ == "__main__":
    main()
