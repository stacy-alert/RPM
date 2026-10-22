"""Daily pipeline entrypoint: scrape -> classify -> merge with prior state -> publish.

Logging rule, enforced by code review not just discipline: nothing in this
file logs a dog's name, CAC ID, or listing URL. Only counts and reference
codes (which are meaningless without lookup.json) are ever printed.
"""

import json
import logging
import os
from pathlib import Path

from scraper import load_config, fetch_shelter, download_photos, ShelterBlockedError
from classifier import classify_dog
from dataset import build_datasets, build_dogs_json
import ftp_sync
import requests

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("main")

HERE = Path(__file__).parent
OVERRIDES_PATH = HERE / "overrides.json"

PUBLIC_REMOTE_DIR = os.environ["BLUEHOST_FTP_DIR"] + "/topsecretproject"
PRIVATE_REMOTE_DIR = os.environ["BLUEHOST_PRIVATE_DIR"]


def main():
    config = load_config()
    overrides = json.loads(OVERRIDES_PATH.read_text()) if OVERRIDES_PATH.exists() else {}

    all_scraped = []
    for shelter in config["shelters"]:
        if not shelter.get("enabled"):
            continue
        try:
            dogs = fetch_shelter(shelter, config)
        except ShelterBlockedError as e:
            log.error("STOPPING for shelter '%s': %s", shelter["name"], e)
            raise SystemExit(1)
        log.info("Shelter '%s': %d dog(s) found.", shelter["name"], len(dogs))
        all_scraped.extend(dogs)

    log.info("Total dogs across all enabled shelters: %d", len(all_scraped))

    session = requests.Session()
    classifications = {}
    classified_count = 0
    for dog in all_scraped:
        photos = download_photos(dog, config, session)
        matches = classify_dog(photos)
        if matches:
            classified_count += 1
        classifications[dog["cac_id"]] = matches
        # photos (the actual bytes) go out of scope here and are never written to disk.

    log.info("Dogs with at least one target-breed match: %d / %d", classified_count, len(all_scraped))

    existing_lookup_raw = ftp_sync.download_text(PRIVATE_REMOTE_DIR, "lookup.json")
    existing_lookup = json.loads(existing_lookup_raw) if existing_lookup_raw else {}
    log.info("Existing lookup.json entries before this run: %d", len(existing_lookup))

    public_dogs, new_lookup = build_datasets(all_scraped, classifications, existing_lookup, overrides)
    dogs_json = build_dogs_json(public_dogs)

    log.info("Publishing dogs.json: %d entries.", len(public_dogs))
    log.info("New lookup.json: %d entries (was %d).", len(new_lookup), len(existing_lookup))

    per_breed_counts = {}
    for d in public_dogs:
        for m in d["looks_like"]:
            per_breed_counts[m["display"]] = per_breed_counts.get(m["display"], 0) + 1
    log.info("Matches per breed: %s", per_breed_counts)

    ftp_sync.upload_text(PUBLIC_REMOTE_DIR, "dogs.json", json.dumps(dogs_json, indent=2))
    ftp_sync.upload_text(PRIVATE_REMOTE_DIR, "lookup.json", json.dumps(new_lookup, indent=2))


if __name__ == "__main__":
    main()
