"""Breed configuration for the shelter breed-ID pipeline.

TARGET_BREEDS maps each breed we actively search for to:
  - code: short prefix used in generated reference codes (e.g. BC-0142)
  - display: human-readable name shown on the site
  - imagenet_labels: the exact ImageNet-1k label string(s) (as returned by
    the torchvision/timm weights' category list) that count as a match for
    this breed. Checked case-insensitively, exact string match.

Verified against the standard torchvision/timm ImageNet-1k category list
(see topsecretproject/README.md for how to re-verify if the model is ever
swapped). Two breeds from the original target list have no usable match
and are intentionally omitted: Australian Shepherd and Australian Cattle
Dog are not ImageNet-1k classes; images of them get misclassified under
unrelated labels (commonly "kelpie" or "collie"), so including them would
just mean confidently wrong guesses. Treeing Walker Coonhound maps to the
closest available label, "Walker hound", not an exact name match, so it
displays as "Walker-type coonhound" rather than claiming precision we
don't have.
"""

TARGET_BREEDS = [
    {"code": "BC", "display": "Border Collie", "imagenet_labels": ["Border collie"]},
    {"code": "BT", "display": "Bluetick Coonhound", "imagenet_labels": ["bluetick"]},
    {"code": "RB", "display": "Redbone Coonhound", "imagenet_labels": ["redbone"]},
    {"code": "BTC", "display": "Black and Tan Coonhound", "imagenet_labels": ["black-and-tan coonhound"]},
    {"code": "WC", "display": "Walker-type coonhound", "imagenet_labels": ["Walker hound, Walker foxhound"]},
    {"code": "GS", "display": "German Shepherd", "imagenet_labels": ["German shepherd, German shepherd dog, German police dog, alsatian"]},
    {"code": "SH", "display": "Siberian Husky", "imagenet_labels": ["Siberian husky"]},
    {"code": "GR", "display": "Golden Retriever", "imagenet_labels": ["golden retriever"]},
    {"code": "LR", "display": "Labrador Retriever", "imagenet_labels": ["Labrador retriever"]},
    {"code": "BG", "display": "Beagle", "imagenet_labels": ["beagle"]},
]

# Dropped per owner decision 2026-10-22 (no clean ImageNet-1k match):
#   Australian Shepherd, Australian Cattle Dog

# Any ImageNet label containing one of these substrings (case-insensitive)
# is hard-filtered out of every classifier result before anything downstream
# — the pipeline's output, the overrides file, and the site — ever sees it.
# This is deliberately broad (substring, not exact-match) so it also catches
# any future ImageNet label we haven't enumerated by name.
EXCLUDED_LABEL_SUBSTRINGS = [
    "staffordshire",
    "pit bull",
    "pitbull",
]


def is_excluded_label(label: str) -> bool:
    lowered = label.lower()
    return any(sub in lowered for sub in EXCLUDED_LABEL_SUBSTRINGS)


def label_to_breed(label: str):
    """Return the TARGET_BREEDS entry matching this exact ImageNet label, or None."""
    for breed in TARGET_BREEDS:
        if label in breed["imagenet_labels"]:
            return breed
    return None
