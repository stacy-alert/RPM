"""Reference-code assignment and dogs.json / lookup.json generation.

Reference codes (e.g. "BC-0142") are assigned once, from the top-ranked
breed match at the time a dog is first seen, and then kept stable for
that dog for as long as it stays listed — even if a later run's
classification would rank a different breed first. This keeps a code
usable in an email or a bookmark without it silently pointing at a
different "looks like" claim tomorrow. If you want codes to track the
current top match instead, that's a one-line change (see README).

lookup.json is the only place a CAC animal ID, name, or listing URL is
ever written. dogs.json is the public file and must never contain those
fields — enforced here by construction, not by a filter: the function
that builds a public dog record simply never reads them from the input.
"""

import re
from datetime import date, datetime, timezone


def _next_sequence_for_prefix(existing_lookup: dict, prefix: str) -> int:
    highest = 0
    for code in existing_lookup:
        match = re.match(rf"^{re.escape(prefix)}-(\d+)$", code)
        if match:
            highest = max(highest, int(match.group(1)))
    return highest + 1


def build_datasets(scraped_dogs: list[dict], classifications: dict, existing_lookup: dict, overrides: dict):
    """
    scraped_dogs: list of dicts from the scraper, each with at least
        cac_id, name, listing_url, sex, age, size, date_listed
    classifications: cac_id -> list of up to 3 {"code","display","confidence"}
        (already pit-bull-filtered and restricted to TARGET_BREEDS, see classifier.py)
    existing_lookup: previously-published lookup.json contents (or {} on first run)
    overrides: overrides.json contents, keyed by reference code

    Returns (public_dogs: list[dict] for dogs.json, new_lookup: dict for lookup.json)
    """
    cac_id_to_code = {entry["cac_id"]: code for code, entry in existing_lookup.items()}

    new_lookup = {}
    public_dogs = []
    seen_cac_ids = set()

    for dog in scraped_dogs:
        cac_id = dog["cac_id"]
        seen_cac_ids.add(cac_id)
        matches = classifications.get(cac_id, [])
        if not matches:
            continue  # no usable photos / no target-breed match above zero confidence

        code = cac_id_to_code.get(cac_id)
        if code is None:
            top_breed_code = matches[0]["code"]
            seq = _next_sequence_for_prefix(existing_lookup, top_breed_code)
            code = f"{top_breed_code}-{seq:04d}"

        override = overrides.get(code, {})
        if override.get("hidden"):
            continue

        new_lookup[code] = {
            "cac_id": cac_id,
            "name": dog["name"],
            "listing_url": dog["listing_url"],
        }

        display_matches = matches
        if override.get("confirmed_breed"):
            display_matches = [{"display": override["confirmed_breed"], "confidence": None, "confirmed": True}]

        public_dogs.append({
            "reference_code": code,
            "looks_like": display_matches,
            "sex": dog.get("sex"),
            "age": dog.get("age"),
            "size": dog.get("size"),
            "date_listed": dog.get("date_listed"),
            "first_seen": existing_lookup.get(code, {}).get("first_seen") or date.today().isoformat(),
        })

    # Carry forward first_seen for dogs that already existed, since the
    # loop above only has it from existing_lookup, not new_lookup, and we
    # want it in the private record too for debugging/ordering if needed.
    for code, entry in new_lookup.items():
        if code in existing_lookup and "first_seen" in existing_lookup[code]:
            entry["first_seen"] = existing_lookup[code]["first_seen"]
        else:
            entry["first_seen"] = next(
                (d["first_seen"] for d in public_dogs if d["reference_code"] == code),
                date.today().isoformat(),
            )

    return public_dogs, new_lookup


def build_dogs_json(public_dogs: list[dict]) -> dict:
    return {
        "last_updated": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "dogs": public_dogs,
    }
