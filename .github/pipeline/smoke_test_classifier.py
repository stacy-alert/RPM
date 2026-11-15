"""One-off smoke test: proves classify_dog() loads the real pretrained
model and runs end to end on real photos of the actual breeds the
pipeline looks for — not just random photos, which mostly miss our
10-breed target list by chance. Touches no CAC data, no FTP, no secret
of any kind — safe to run anytime with nothing configured. Uses dog.ceo
(a free public API, unrelated to CAC) purely as a source of real photos,
matched to TARGET_BREEDS by name rather than hardcoded, so this keeps
working if the breed list changes.
"""

import requests

from breeds import TARGET_BREEDS
from classifier import classify_dog

STOPWORDS = {"type"}


def _dog_ceo_breed_list() -> dict:
    resp = requests.get("https://dog.ceo/api/breeds/list/all", timeout=15)
    resp.raise_for_status()
    return resp.json()["message"]


def _find_matching_endpoint(display_name: str, breed_list: dict) -> str | None:
    """Best-effort match of one target breed to a dog.ceo breed/sub-breed
    path, by substring on each distinctive word of the display name."""
    words = [
        w.lower() for w in display_name.replace("-", " ").split()
        if len(w) > 3 and w.lower() not in STOPWORDS
    ]
    for breed, sub_breeds in breed_list.items():
        if sub_breeds:
            for sub in sub_breeds:
                if any(w in breed or w in sub for w in words):
                    return f"https://dog.ceo/api/breed/{breed}/{sub}/images/random"
        elif any(w in breed for w in words):
            return f"https://dog.ceo/api/breed/{breed}/images/random"
    return None


def main():
    breed_list = _dog_ceo_breed_list()

    matched = [
        (breed["display"], endpoint)
        for breed in TARGET_BREEDS
        if (endpoint := _find_matching_endpoint(breed["display"], breed_list))
    ]
    print(f"Matched {len(matched)}/{len(TARGET_BREEDS)} target breeds to a real dog.ceo photo source.\n")

    for expected_breed, endpoint in matched:
        img_resp = requests.get(endpoint, timeout=15)
        img_resp.raise_for_status()
        photo_url = img_resp.json()["message"]
        photo = requests.get(photo_url, timeout=15).content

        matches = classify_dog([photo])
        print(f"Expected: {expected_breed}")
        print(f"  {photo_url}")
        if not matches:
            print("  no target-breed match above zero confidence")
        for m in matches:
            print(f"  -> {m['display']:<24} {m['confidence']:.1%}  [{m['code']}]")
        print()


if __name__ == "__main__":
    main()
