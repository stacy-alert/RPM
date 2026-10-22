"""Polite scraper for shelter adoptable-dog listing pages.

Ground rules, non-negotiable:
  - Identify ourselves honestly (User-Agent names the project + a contact
    email from shelters_config.json).
  - Wait request_delay_seconds between every request, including between
    paginated listing pages and individual dog detail pages.
  - If the site responds with anything that looks like a block (403, 429,
    or a CAPTCHA/"access denied" page), stop immediately and raise
    ShelterBlockedError. Do not retry with different headers, rotate
    anything, or otherwise try to get around a block — that's the
    explicit instruction this was built under.

The CAC selectors in shelters_config.json are placeholders. CACParser
below is written so that once real page HTML is available, only the
selectors (or, if the real structure doesn't fit a flat CSS-selector
model, the body of `parse_listing_page`/`parse_detail_page`) need to
change — the politeness/pagination/error-handling scaffolding stays as-is.
"""

import json
import logging
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("scraper")

CONFIG_PATH = Path(__file__).parent / "shelters_config.json"


class ShelterBlockedError(Exception):
    """Raised when a shelter site appears to be blocking us. Never caught-and-retried."""


def load_config() -> dict:
    with open(CONFIG_PATH) as f:
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
    time.sleep(config["request_delay_seconds"])
    response = session.get(url, headers={"User-Agent": _user_agent(config)}, timeout=20)
    if _looks_blocked(response):
        raise ShelterBlockedError(
            f"{url} returned a response that looks like a block "
            f"(status {response.status_code}). Stopping — not attempting to work around it. "
            f"Tell the site owner's project maintainer; this shelter's scrape is paused "
            f"until investigated."
        )
    response.raise_for_status()
    return response


class CACParser:
    """Parser for Cincinnati Animal CARE's adopt-a-dog listing.

    PLACEHOLDER — selectors are not yet verified against real markup.
    Replace the CSS selectors in shelters_config.json, or rewrite the
    methods below directly if CAC's actual page structure doesn't fit
    a flat selector model (e.g. if data is embedded in a JS data blob
    rather than plain HTML).
    """

    def __init__(self, shelter_config: dict):
        self.config = shelter_config
        self.selectors = shelter_config["selectors"]

    def parse_listing_page(self, html: str) -> list[dict]:
        soup = BeautifulSoup(html, "html.parser")
        cards = soup.select(self.selectors["dog_card"])
        dogs = []
        for card in cards:
            dogs.append(self._parse_card(card))
        return dogs

    def _parse_card(self, card) -> dict:
        def text_of(selector):
            el = card.select_one(selector)
            return el.get_text(strip=True) if el else None

        def attr_of(selector, attr):
            el = card.select_one(selector)
            return el.get(attr) if el else None

        listing_url = attr_of(self.selectors["listing_url"], "href")
        return {
            "name": text_of(self.selectors["name"]),
            "listing_url": listing_url,
            "cac_id": self._extract_cac_id(listing_url),
            "photo_urls": [img.get("src") for img in card.select(self.selectors["photo_urls"])],
            "sex": text_of(self.selectors["sex"]),
            "age": text_of(self.selectors["age"]),
            "size": text_of(self.selectors["size"]),
            "date_listed": text_of(self.selectors["date_listed"]),
        }

    @staticmethod
    def _extract_cac_id(listing_url: str) -> str:
        """Best-effort extraction of CAC's internal animal ID from the listing URL.

        PLACEHOLDER — needs real URL examples to get right. Falls back to
        the full URL itself if no ID-shaped segment is found, so dogs are
        never silently dropped, but reference-code stability depends on
        this being a real stable ID rather than the whole URL.
        """
        if not listing_url:
            return None
        import re
        match = re.search(r"(\d{3,})", listing_url)
        return match.group(1) if match else listing_url

    def find_next_page(self, html: str) -> str | None:
        """Return the next listing page's URL, or None if this is the last page."""
        next_selector = self.selectors.get("next_page_link")
        if not next_selector:
            return None
        soup = BeautifulSoup(html, "html.parser")
        next_link = soup.select_one(next_selector)
        return next_link.get("href") if next_link else None


def fetch_shelter(shelter_config: dict, config: dict) -> list[dict]:
    """Fetch and parse all adoptable dogs for one shelter. Paginates until no next page."""
    session = requests.Session()
    parser = CACParser(shelter_config)  # only parser we have right now; dispatch on shelter id once more exist

    all_dogs = []
    url = shelter_config["listing_url"]
    page_num = 1
    while url:
        log.info("Fetching %s page %d: %s", shelter_config["name"], page_num, url)
        response = polite_get(url, config, session)
        page_dogs = parser.parse_listing_page(response.text)
        log.info("  found %d dog(s) on this page", len(page_dogs))
        all_dogs.extend(page_dogs)
        url = parser.find_next_page(response.text)
        page_num += 1

    return all_dogs


def download_photos(dog: dict, config: dict, session: requests.Session) -> list[bytes]:
    """Download one dog's photos to memory only. Caller must not write these to disk."""
    photo_bytes = []
    for photo_url in dog.get("photo_urls") or []:
        if not photo_url:
            continue
        response = polite_get(photo_url, config, session)
        photo_bytes.append(response.content)
    return photo_bytes
