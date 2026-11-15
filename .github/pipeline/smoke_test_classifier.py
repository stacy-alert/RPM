"""One-off smoke test: proves classify_dog() loads the real pretrained
model and runs end to end on real photos. Downloads a handful of random
dog photos from dog.ceo (a free public API, unrelated to CAC) purely for
this test. Touches no CAC data, no FTP, no secret of any kind — safe to
run anytime with nothing configured.
"""

import requests

from classifier import classify_dog

PHOTO_COUNT = 5


def main():
    resp = requests.get(f"https://dog.ceo/api/breeds/image/random/{PHOTO_COUNT}", timeout=15)
    resp.raise_for_status()
    urls = resp.json()["message"]

    for url in urls:
        photo = requests.get(url, timeout=15).content
        matches = classify_dog([photo])
        print(f"\n{url}")
        if not matches:
            print("  no target-breed match above zero confidence")
        for m in matches:
            print(f"  {m['display']:<24} {m['confidence']:.1%}  [{m['code']}]")


if __name__ == "__main__":
    main()
