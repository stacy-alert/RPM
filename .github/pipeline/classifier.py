"""CPU image classification against ImageNet-1k, restricted to our target breed list.

Uses timm's pretrained weights (open-source, free, no API key). Photos are
passed in as in-memory bytes and never written to disk — callers are
responsible for not persisting the raw photo bytes anywhere.
"""

import io
import logging

import torch
from PIL import Image

from breeds import TARGET_BREEDS, is_excluded_label

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("classifier")

# Balance of accuracy vs. CPU speed for a daily batch job over ~100+ dogs.
MODEL_NAME = "resnet50.a1_in1k"

_model = None
_transform = None
_class_labels = None


def _load_model():
    global _model, _transform, _class_labels
    if _model is not None:
        return
    import timm
    from timm.data import resolve_data_config
    from timm.data.transforms_factory import create_transform

    log.info("Loading classifier model %s (CPU)...", MODEL_NAME)
    _model = timm.create_model(MODEL_NAME, pretrained=True)
    _model.eval()

    config = resolve_data_config({}, model=_model)
    _transform = create_transform(**config)

    # Pull the official ImageNet-1k label strings from timm's own bundled
    # metadata (timm.data.ImageNetInfo) rather than hand-typing a 1000-entry
    # list, which would be impossible to verify for correctness.
    # label_names() returns synset IDs (e.g. "n02106166"); label_descriptions()
    # returns the human-readable comma-joined names used throughout this
    # pipeline and verified against breeds.py — confirmed empirically with
    # timm 1.0.30 before relying on it here.
    try:
        from timm.data import ImageNetInfo
        info = ImageNetInfo()
        _class_labels = info.label_descriptions()
    except Exception as e:
        raise RuntimeError(
            "Could not load ImageNet-1k label descriptions from "
            "timm.data.ImageNetInfo(). Run `python -c \"from timm.data import "
            "ImageNetInfo; print(ImageNetInfo().label_descriptions()[:5])\"` "
            "to debug directly rather than guessing at a replacement label list."
        ) from e
    log.info("Classifier ready (%d classes).", len(_class_labels))


def _classify_one_photo(photo_bytes: bytes) -> torch.Tensor:
    """Return a 1000-length probability tensor for one in-memory photo."""
    _load_model()
    img = Image.open(io.BytesIO(photo_bytes)).convert("RGB")
    tensor = _transform(img).unsqueeze(0)
    with torch.no_grad():
        logits = _model(tensor)
        probs = torch.softmax(logits, dim=1)[0]
    return probs


def classify_dog(photo_bytes_list: list[bytes]) -> list[dict]:
    """Classify all of one dog's photos, average, return top-3 TARGET_BREEDS matches.

    Returns a list of up to 3 dicts: {"code", "display", "confidence"},
    sorted by confidence descending, restricted to TARGET_BREEDS only.
    Pit-bull-type labels are zeroed out of the raw probability vector
    before any ranking happens, so they can never surface here even if
    TARGET_BREEDS is edited in the future to include something adjacent.
    """
    if not photo_bytes_list:
        return []

    _load_model()
    summed = torch.zeros(len(_class_labels))
    used = 0
    for photo_bytes in photo_bytes_list:
        try:
            probs = _classify_one_photo(photo_bytes)
        except Exception as e:
            log.warning("Skipping unreadable photo: %s", e)
            continue
        summed += probs
        used += 1

    if used == 0:
        return []

    averaged = summed / used

    # Zero out excluded (pit-bull-type) labels before any ranking at all.
    for idx, label in enumerate(_class_labels):
        if is_excluded_label(label):
            averaged[idx] = 0.0

    # Score only our target breeds, not the full 1000-class space — the
    # product is "which of these breeds does this dog look like", not
    # "what is the single most likely ImageNet class" (which would often
    # be something irrelevant like a dog bed or a tennis ball).
    scored = []
    for breed in TARGET_BREEDS:
        best_label_prob = 0.0
        for label in breed["imagenet_labels"]:
            if label in _class_labels:
                idx = _class_labels.index(label)
                best_label_prob = max(best_label_prob, float(averaged[idx]))
        scored.append((breed, best_label_prob))

    scored.sort(key=lambda pair: pair[1], reverse=True)
    top3 = scored[:3]
    return [
        {"code": breed["code"], "display": breed["display"], "confidence": round(conf, 4)}
        for breed, conf in top3
        if conf > 0
    ]
