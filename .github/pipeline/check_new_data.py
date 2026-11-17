"""Gate for the hourly workflow: is there a shelter list we haven't processed?

Standard library only (no torch install needed), so an hourly check with
nothing new costs a few seconds. Compares the uploaded list's fetched_at
(cac_raw.json, written by the Send dogs bookmark or the Pi) with the one
main.py recorded after its last successful publish (last_processed.txt).
Writes new=true/false to $GITHUB_OUTPUT. A manual run always processes.
"""

import json
import logging
import os
from datetime import datetime

import ftp_sync

logging.basicConfig(level=logging.INFO)


def set_output(value: bool):
    path = os.environ.get("GITHUB_OUTPUT")
    if path:
        with open(path, "a") as f:
            f.write(f"new={'true' if value else 'false'}\n")


def parse(ts: str):
    return datetime.fromisoformat(ts.strip().replace("Z", "+00:00"))


def main():
    if os.environ.get("GITHUB_EVENT_NAME") == "workflow_dispatch":
        print("Manual run: processing the latest list regardless.")
        set_output(True)
        return
    private = ftp_sync.private_dir()
    raw = ftp_sync.download_text(private, "cac_raw.json")
    if not raw:
        print("No uploaded shelter list yet. Nothing to do.")
        set_output(False)
        return
    fetched = json.loads(raw)["fetched_at"]
    last = ftp_sync.download_text(private, "last_processed.txt")
    if last and parse(last) == parse(fetched):
        print(f"No new list since {fetched}. Skipping.")
        set_output(False)
        return
    print(f"New list taken {fetched} (last processed: {last.strip() if last else 'never'}). Processing.")
    set_output(True)


if __name__ == "__main__":
    main()
