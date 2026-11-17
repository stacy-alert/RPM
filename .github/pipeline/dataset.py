"""Reference-code assignment and dogs.json / lookup.json generation.

Reference codes (e.g. "BC-0142") are assigned once, from the top-ranked
breed match at the time a dog is first seen, and then kept stable for
that dog for as long as it stays listed — even if a later run's
classification would rank a different breed first. This keeps a code
usable in an email or a bookmark without it silently pointing at a
different "looks like" claim tomorrow. If you want codes to track the
current top match instead, that's a one-line change (see README).

Owner decision 2026-11-16: while the email inquiry form is unconfigured,
dogs.json also carries each dog's name, shelter_seq_id (CAC's own public
sequential ID), and listing_url, so cards can show "Ask about this dog"
information (name, ID, a link to the real listing) without email. This
is a deliberate reversal of the original minimal-disclosure design, made
with the ToS's no-republish/no-hyperlink risk flagged and accepted. The
AnimalsFirst internal cac_id (never shown anywhere in CAC's own UI,
meaningless to a visitor) is still kept out of the public file — only
lookup.json (private, FTP'd outside public_html) carries it, for the
email flow if/when it's reconfigured.
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

    # Seed a per-prefix high-water mark from existing codes, then bump it as
    # we assign new ones this run, so two dogs never collide on e.g. BC-0001.
    prefix_max = {}
    for code in existing_lookup:
        m = re.match(r"^([A-Za-z]+)-(\d+)$", code)
        if m:
            prefix_max[m.group(1)] = max(prefix_max.get(m.group(1), 0), int(m.group(2)))

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
            seq = prefix_max.get(top_breed_code, 0) + 1
            prefix_max[top_breed_code] = seq
            code = f"{top_breed_code}-{seq:04d}"

        override = overrides.get(code, {})
        if override.get("hidden"):
            continue

        new_lookup[code] = {
            "cac_id": cac_id,
            "shelter_seq_id": dog.get("shelter_seq_id"),
            "name": dog["name"],
            "listing_url": dog["listing_url"],
        }

        display_matches = matches
        if override.get("confirmed_breed"):
            display_matches = [{"display": override["confirmed_breed"], "confidence": None, "confirmed": True}]

        public_dogs.append({
            "reference_code": code,
            "name": dog.get("name"),
            "shelter_seq_id": dog.get("shelter_seq_id"),
            "listing_url": dog.get("listing_url"),
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


def build_dogs_json(public_dogs: list[dict], data_as_of: str | None = None,
                    list_fetched_at: str | None = None) -> dict:
    result = {
        "last_updated": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "dogs": public_dogs,
    }
    if data_as_of:
        result["data_as_of"] = data_as_of
    if list_fetched_at:
        result["list_fetched_at"] = list_fetched_at
    return result
