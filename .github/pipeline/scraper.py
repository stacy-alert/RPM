"""Scraper for shelter adoptable-dog listing pages.

Ground rules, non-negotiable:
  - Identify ourselves honestly to the shelter's own server (User-Agent
    names the project + a contact email from shelters_config.json).
  - Wait request_delay_seconds between requests TO THE SHELTER'S OWN SITE.
    This does not apply to fetching photo bytes from AnimalsFirst's S3
    bucket afterward — that's neutral CDN infrastructure at AWS scale, not
    the shelter's own small WordPress install, so there's no politeness
    reason to slow those down the same way.
  - If the site responds with anything that looks like a block (403, 429,
    or a CAPTCHA/"access denied" page), stop immediately and raise
    ShelterBlockedError. Do not retry with different headers, rotate
    anything, or otherwise try to get around a block.

CAC's listing page (built on the PetMatchPro WordPress plugin) puts every
field we need directly on each dog's card as data-* attributes — name,
AnimalsFirst animal ID, CAC's own sequential ID, sex, age, size, intake
date, listing URL, and up to 5 photo URLs — so no per-dog detail-page
fetch is needed at all. This was confirmed against real saved HTML from
the site, not guessed.

Pagination is NOT yet handled: fetch_shelter does a single plain GET of
the listing URL and reports how many dog cards it finds versus how many
the page itself claims to have ("N Potential Companions"), so a shortfall
is visible rather than silent. If the real site only server-renders a
partial list and loads the rest via scroll-triggered AJAX, this will
under-count — see the logged comparison and topsecretproject/README.md.
"""

import logging
import re
import time

import requests
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("scraper")

SIZE_DISPLAY = {"s": "Small", "m": "Medium", "l": "Large", "xl": "Extra Large"}


class ShelterBlockedError(Exception):
    """Raised when a shelter site appears to be blocking us. Never caught-and-retried."""


def load_config():
    import json
    from pathlib import Path
    with open(Path(__file__).parent / "shelters_config.json") as f:
        return json.load(f)


def _user_agent(config: dict) -> str:
    return f"{config['project_name']} ({config['contact_email']})"


def _looks_blocked(response: requests.Response) -> bool:
    if response.status_code in (403, 429, 503):
        return True
    body_lower = response.text[:5000].lower()
    block_markers = ["captcha", "access denied", "checking your browser", "cloudflare"]
    return any(marker in body_lower for marker in block_markers)


def polite_get(url: str, config: dict, session: requests.Session) -> requests.Response:
    """Use for requests to the shelter's own site only — see module docstring."""
    time.sleep(config["request_delay_seconds"])
    response = session.get(url, headers={"User-Agent": _user_agent(config)}, timeout=20)
    if _looks_blocked(response):
        raise ShelterBlockedError(
            f"{url} returned a response that looks like a block "
            f"(status {response.status_code}). Stopping — not attempting to work around it."
        )
    response.raise_for_status()
    return response


def fast_get(url: str, config: dict, session: requests.Session) -> requests.Response:
    """Use for neutral CDN/storage fetches (photo bytes) — no artificial delay."""
    response = session.get(url, headers={"User-Agent": _user_agent(config)}, timeout=20)
    response.raise_for_status()
    return response


class CACParser:
    """Parser for Cincinnati Animal CARE's PetMatchPro-powered dog listing.

    Confirmed against real saved HTML (2026-10) — see the data-* attribute
    names below, all read directly off each `.pmp-search-result-container`.
    """

    def parse_listing_page(self, html: str) -> tuple[list[dict], int | None]:
        """Returns (dogs, claimed_total). claimed_total is the number the
        page itself displays (e.g. "428 Potential Companions"), or None if
        that element isn't found — used purely to detect a pagination
        shortfall, not for anything functional."""
        soup = BeautifulSoup(html, "html.parser")

        claimed_total = None
        count_el = soup.select_one(".pmp-search-profile-count")
        if count_el:
            match = re.search(r"(\d+)", count_el.get_text())
            if match:
                claimed_total = int(match.group(1))

        dogs = []
        for card in soup.select(".pmp-search-result-container"):
            dog = self._parse_card(card)
            if dog:
                dogs.append(dog)
        return dogs, claimed_total

    def _parse_card(self, card) -> dict | None:
        if card.get("data-species") != "dog" or card.get("data-status") != "available":
            return None

        cac_id = card.get("data-id") or card.get("data-animal-id")
        if not cac_id:
            return None

        name_link = card.select_one(".pmp-search-result-name-link")
        listing_url = name_link.get("href") if name_link else None

        photo_urls = []
        for key in ("data-photourl", "data-photourl1", "data-photourl2", "data-photourl3", "data-photourl4"):
            url = card.get(key)
            if url and url not in photo_urls:
                photo_urls.append(url)

        size_code = card.get("data-afsize")
        size = SIZE_DISPLAY.get(size_code, size_code)

        age_bucket = card.get("data-afage")
        age = age_bucket.capitalize() if age_bucket else None

        sex = card.get("data-gender")
        sex = sex.capitalize() if sex else None

        return {
            "cac_id": cac_id,
            "shelter_seq_id": card.get("data-seqid"),
            "name": card.get("data-animal-name") or card.get("data-name"),
            "listing_url": listing_url,
            "photo_urls": photo_urls,
            "sex": sex,
            "age": age,
            "size": size,
            "date_listed": card.get("data-intakedate"),
        }


PARSERS = {"cac": CACParser}


def fetch_shelter(shelter_config: dict, config: dict) -> list[dict]:
    """Fetch and parse one shelter's listing. Single page only for now —
    logs the claimed-vs-found comparison so a pagination shortfall is visible."""
    session = requests.Session()
    parser_cls = PARSERS[shelter_config["parser"]]
    parser = parser_cls()

    url = shelter_config["listing_url"]
    log.info("Fetching %s: %s", shelter_config["name"], url)
    response = polite_get(url, config, session)
    dogs, claimed_total = parser.parse_listing_page(response.text)

    log.info("Plain fetch found %d dog card(s).", len(dogs))
    if claimed_total is not None:
        log.info("Page itself claims %d total. Difference: %d", claimed_total, claimed_total - len(dogs))
        if len(dogs) < claimed_total:
            log.warning(
                "Found fewer dogs than the page claims — this listing likely "
                "loads more via scroll-triggered requests that a plain fetch "
                "doesn't trigger. Pagination is not implemented yet; see README."
            )
    else:
        log.info("Could not find the page's own total-count element to compare against.")

    return dogs


def download_photos(dog: dict, config: dict, session: requests.Session) -> list[bytes]:
    """Download one dog's photos to memory only. Caller must not write these to disk."""
    photo_bytes = []
    for photo_url in dog.get("photo_urls") or []:
        try:
            response = fast_get(photo_url, config, session)
            photo_bytes.append(response.content)
        except Exception as e:
            log.warning("Could not fetch a photo (skipping it): %s", e)
    return photo_bytes
