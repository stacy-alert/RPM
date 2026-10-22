# Shelter Breed Preview — prototype

A hidden sub-site at `/topsecretproject/` that reads Cincinnati Animal
CARE's public adoptable-dog pages once a day, guesses breed from photos
using an open-source image classifier, and lets visitors search by
"looks like" breed — for breed rescues and experienced adopters who can't
find breed-typed dogs in a shelter's general listing.

**Status: proof of concept, built without CAC's express permission to
scrape their site.** See the top-level project history / commit messages
for the reasoning; if this proves useful, the next step is asking CAC for
a formal data-sharing agreement.

## Before this can run for real

Two things are placeholders until you fill them in — nothing will work
until both are done:

### 1. CAC page selectors (`.github/pipeline/shelters_config.json`)

The scraper's CSS selectors are all `"TODO"` because this was built in an
environment that couldn't reach `cincinnatianimalcare.org` to see the real
page markup. To finish this:

1. View-source (or save) CAC's `/adopt/` listing page and a single dog's
   detail page.
2. Fill in each selector in `shelters_config.json` — or, if the real
   structure doesn't fit a flat "one selector per field" model (e.g. data
   embedded in a JavaScript blob instead of plain HTML), rewrite
   `CACParser.parse_listing_page` / `_parse_card` in
   `.github/pipeline/scraper.py` directly.
3. Fix `_extract_cac_id` in the same file once you know what a real CAC
   listing URL looks like — reference-code stability depends on this
   being a real stable per-dog ID, not a guess.
4. Replace `contact_email` in `shelters_config.json` with a real address —
   it goes in the scraper's User-Agent string so CAC can reach you if
   there's ever a question about the traffic.

### 2. A verified path outside `public_html`

`lookup.json` (names, CAC IDs, listing URLs) and `.htpasswd` must live
somewhere the web server will never serve over HTTP. Do **not** reuse a
relative `../` guess — this Bluehost account's FTP login has, more than
once during this project, landed somewhere other than expected, and a
wrong guess here would make private data public.

To confirm the real path:
1. In cPanel File Manager, create a folder outside `public_html` (e.g. a
   sibling of it, at the account root).
2. Note cPanel's own path breadcrumb for that folder — that's your
   `BLUEHOST_PRIVATE_ABSOLUTE_PATH` (e.g. `/home2/youraccount/private_data`).
3. Figure out what that same folder's path looks like *relative to where
   this FTP account's login lands* (test with a throwaway file upload and
   confirm its on-disk location in File Manager before trusting it) —
   that's `BLUEHOST_PRIVATE_DIR`. These two are not necessarily the same
   string, even though they point at the same folder.

## Required GitHub repository secrets

Reuses the main site's FTP secrets, plus these new ones:

| Secret | What it's for |
|---|---|
| `BLUEHOST_PRIVATE_DIR` | FTP-relative path to the outside-webroot folder (see above) |
| `BLUEHOST_PRIVATE_ABSOLUTE_PATH` | Real server filesystem path to the same folder (see above) |
| `TOPSECRETPROJECT_PASSWORD` | The password-gate password (username is fixed as `preview`) |
| `BLUEHOST_SMTP_HOST` / `BLUEHOST_SMTP_PORT` / `BLUEHOST_SMTP_USERNAME` / `BLUEHOST_SMTP_PASSWORD` | Bluehost email account credentials for authenticated SMTP (the "Ask about this dog" form) |
| `NOTIFY_EMAIL_TO` | Where "Ask about this dog" inquiries get sent |

## Running it

- **Automatically**: `.github/workflows/topsecretproject-refresh.yml` runs
  once daily, plus whenever you trigger it manually from the Actions tab.
- **Locally**, for testing the classifier/dataset logic without hitting
  the real site: `cd .github/pipeline && pip install -r requirements.txt`,
  then import `classifier.classify_dog()` directly with a local image file's
  bytes, or point `scraper.py` at a saved local HTML file instead of a
  live URL.

## Adding another shelter

Add an entry to the `shelters` list in `shelters_config.json` with its own
`listing_url` and `selectors`. If its page structure doesn't resemble
CAC's, you'll likely need a new parser class in `scraper.py` rather than
reusing `CACParser` — the scraper dispatches on shelter id, so plug a new
parser in alongside it.

## Adding or changing target breeds

Edit `TARGET_BREEDS` in `.github/pipeline/breeds.py`. Each entry needs the
*exact* ImageNet-1k label string(s), verified against the model you're
using — don't guess at label text. To check:

```python
from timm.data import ImageNetInfo
descs = ImageNetInfo().label_descriptions()
[d for d in descs if "your breed name" in d.lower()]
```

If nothing comes back, that breed has no clean match in this model's
label set (this is why Australian Shepherd and Australian Cattle Dog
were dropped) — don't force a near-miss label onto it.

## Editing overrides

`.github/pipeline/overrides.json`, keyed by reference code (e.g.
`BC-0142` — find it on a dog's card, or by searching workflow run logs for
the per-breed counts, which name codes but never names/IDs/URLs):

```json
{
  "BC-0142": { "confirmed_breed": "Border Collie" },
  "GS-0007": { "hidden": true }
}
```

`confirmed_breed` replaces the model's top-3 with a single confirmed
label (no percentage shown, since it's not a guess anymore).
`hidden: true` removes the dog from `dogs.json` entirely.

## Rotating keys

- **Bluehost FTP / SMTP passwords**: change them in cPanel, update the
  matching GitHub secret. Next run picks it up automatically.
- **Password-gate password**: update `TOPSECRETPROJECT_PASSWORD`, next
  run regenerates `.htpasswd` on the server. The old password stops
  working the moment that run completes.

## Known gaps / things not verified in this environment

- CAC's actual page selectors (see above) — untested against real markup.
- The classifier model (`resnet50.a1_in1k` via timm) was verified for
  correct label strings and filter behavior, but a full inference run
  could not be tested here because this build environment couldn't reach
  Hugging Face Hub (where timm downloads pretrained weights from) — a
  normal GitHub Actions runner has unrestricted internet access and won't
  hit this.
- The `.htpasswd` format used is `{SHA}` (plain SHA1, base64) — one of
  Apache's documented basic-auth hash formats, chosen because it needs no
  external `htpasswd` binary. If this specific Bluehost account's Apache
  config rejects it, the fallback is installing `apache2-utils` in the
  workflow and shelling out to the real `htpasswd` tool for apr1-MD5
  instead.
