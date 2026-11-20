"""Daily pipeline entrypoint: scrape -> classify -> merge with prior state -> publish.

Logging rule, enforced by code review not just discipline: nothing in this
file logs a dog's name, CAC ID, or listing URL. Only counts and reference
codes (which are meaningless without lookup.json) are ever printed. Note
this is about *logs*, not the published dogs.json itself -- see dataset.py
for the 2026-11-16 owner decision to publish name/shelter_seq_id/listing_url
there while the email form is unconfigured.
"""

import json
import logging
import os
from pathlib import Path
from urllib.parse import urlsplit

from scraper import load_config, fetch_shelter, download_photos, fast_get, ShelterBlockedError
from classifier import classify_dog
from dataset import build_datasets, build_dogs_json
import ftp_sync
import requests

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("main")

HERE = Path(__file__).parent
OVERRIDES_PATH = HERE / "overrides.json"

ftp_sync.require_env(
    "BLUEHOST_FTP_SERVER", "BLUEHOST_FTP_USERNAME", "BLUEHOST_FTP_PASSWORD", "BLUEHOST_FTP_DIR",
)

PUBLIC_REMOTE_DIR = os.environ["BLUEHOST_FTP_DIR"] + "/topsecretproject"
PRIVATE_REMOTE_DIR = os.environ.get("BLUEHOST_PRIVATE_DIR") or ftp_sync.DEFAULT_PRIVATE_DIRNAME
PHOTOS_REMOTE_DIR = PUBLIC_REMOTE_DIR + "/photos"

_CONTENT_TYPE_EXT = {
    "image/jpeg": "jpg", "image/jpg": "jpg", "image/png": "png",
    "image/webp": "webp", "image/gif": "gif", "image/bmp": "bmp",
}


def _photo_extension(response: requests.Response) -> str:
    content_type = response.headers.get("Content-Type", "").split(";")[0].strip().lower()
    if content_type in _CONTENT_TYPE_EXT:
        return _CONTENT_TYPE_EXT[content_type]
    path = urlsplit(response.url).path.lower()
    for ext in ("jpeg", "jpg", "png", "webp", "gif", "bmp"):
        if path.endswith("." + ext):
            return "jpg" if ext == "jpeg" else ext
    return "jpg"


def main():
    # Defense in depth: the workflow already runs this check in a separate
    # step before this script, but this script uploads lookup.json too and
    # should never do so without re-confirming the path is safe, in case
    # it's ever run standalone or the workflow steps get reordered. Already
    # created by that earlier step, so this is just a re-verification.
    ftp_sync.ensure_private_dir(PRIVATE_REMOTE_DIR)

    config = load_config()
    overrides = json.loads(OVERRIDES_PATH.read_text()) if OVERRIDES_PATH.exists() else {}

    all_scraped = []
    data_as_of = None
    list_fetched_at = None
    for shelter in config["shelters"]:
        if not shelter.get("enabled"):
            continue
        try:
            dogs = fetch_shelter(shelter, config)
        except ShelterBlockedError as e:
            log.error("STOPPING for shelter '%s': %s", shelter["name"], e)
            raise SystemExit(1)
        if shelter.get("source") == "snapshot" and not data_as_of:
            data_as_of = shelter.get("snapshot_date")
        if shelter.get("_fetched_at") and not list_fetched_at:
            list_fetched_at = shelter["_fetched_at"]
        if shelter.get("_stale") and not data_as_of:
            data_as_of = shelter["_fetched_at"].strftime("%B %-d, %Y")
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

    # Host one photo per published dog ourselves rather than linking to the
    # shelter's own copy -- fetched fresh here (not reused from the
    # classification download above) specifically so this is always the
    # photo_urls[0] the owner asked for, not whichever photo happened to
    # download successfully first during classification. Only published
    # dogs get a photo fetched/uploaded -- most scraped dogs never make it
    # into public_dogs at all (see MATCH_THRESHOLD in classifier.py).
    scraped_by_cac_id = {d["cac_id"]: d for d in all_scraped}
    if public_dogs:
        ftp_sync.ensure_dir(PHOTOS_REMOTE_DIR)
    photo_count = 0
    for dog in public_dogs:
        cac_id = new_lookup[dog["reference_code"]]["cac_id"]
        photo_urls = scraped_by_cac_id.get(cac_id, {}).get("photo_urls") or []
        dog["photo_url"] = None
        if not photo_urls:
            continue
        try:
            response = fast_get(photo_urls[0], config, session)
            filename = f"{dog['reference_code']}.{_photo_extension(response)}"
            ftp_sync.upload_binary(PHOTOS_REMOTE_DIR, filename, response.content)
            dog["photo_url"] = f"photos/{filename}"
            photo_count += 1
        except Exception as e:
            log.warning("Could not fetch/host a photo for a published dog (showing placeholder): %s", e)
    log.info("Hosted a photo for %d / %d published dog(s).", photo_count, len(public_dogs))

    dogs_json = build_dogs_json(public_dogs, data_as_of=data_as_of,
                                list_fetched_at=list_fetched_at.isoformat() if list_fetched_at else None)

    # Every run publishes only dogs in the current list, so dogs that left
    # the shelter's page (adopted, transferred) drop off here. Log how many.
    dropped = sorted(set(existing_lookup) - set(new_lookup))
    log.info("Dropped since last run (no longer listed, or no longer matching): %d %s",
             len(dropped), dropped)

    log.info("Publishing dogs.json: %d entries.", len(public_dogs))
    log.info("New lookup.json: %d entries (was %d).", len(new_lookup), len(existing_lookup))

    per_breed_counts = {}
    for d in public_dogs:
        for m in d["looks_like"]:
            per_breed_counts[m["display"]] = per_breed_counts.get(m["display"], 0) + 1
    log.info("Matches per breed: %s", per_breed_counts)

    raisin_present = any(d.get("shelter_seq_id") == "56033" for d in all_scraped)
    log.info("Dog with shelter_seq_id 56033 (Raisin, per project start) present in this run: %s", raisin_present)

    ftp_sync.upload_text(PUBLIC_REMOTE_DIR, "dogs.json", json.dumps(dogs_json, indent=2))
    ftp_sync.upload_text(PRIVATE_REMOTE_DIR, "lookup.json", json.dumps(new_lookup, indent=2))
    if list_fetched_at:
        # Tells the hourly check (check_new_data.py) this list is done.
        ftp_sync.upload_text(PRIVATE_REMOTE_DIR, "last_processed.txt", list_fetched_at.isoformat())


if __name__ == "__main__":
    main()
