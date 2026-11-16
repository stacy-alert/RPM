# Shelter Breed Preview — prototype

A public-but-unlisted sub-site at `/topsecretproject/` (noindex, no nav
link from the main site, no robots.txt entry) that reads Cincinnati
Animal CARE's public adoptable-dog listing once a day, guesses breed from
photos using an open-source image classifier, and lets visitors search by
"looks like" breed — for breed rescues and experienced adopters who can't
find breed-typed dogs in a shelter's general listing.

No password gate — the folder is reachable by anyone who has the URL, but
isn't indexed and isn't linked from anywhere.

**Status: proof of concept, built without CAC's express permission to
scrape their site.** If this proves useful, the next step is asking CAC
for a formal data-sharing agreement.

## How CAC's site actually works (confirmed against real saved HTML)

CAC's listing (`/adopt/dogs/`) runs on the PetMatchPro WordPress plugin.
Every dog's card is a `.pmp-search-result-container` element carrying
everything we need directly as `data-*` attributes — no per-dog detail
page fetch required:

| Field | Source attribute |
|---|---|
| Stable internal ID | `data-id` (AnimalsFirst's own animal ID) |
| Shelter's own ID | `data-seqid` (e.g. `56033` for Raisin — matches the number given at project start) |
| Name | `data-animal-name` |
| Sex | `data-gender` |
| Age bucket | `data-afage` (baby/young/adult/senior) |
| Size bucket | `data-afsize` (s/m/l/xl) |
| Date listed (proxy) | `data-intakedate` |
| Photos (up to 5) | `data-photourl`, `data-photourl1`..`data-photourl4`, hosted on `animalsfirstprod.s3.amazonaws.com` |
| Listing URL | the `.pmp-search-result-name-link` href |

`scraper.py`'s `CACParser` implements this directly — see it for the
real, tested code rather than a selector-config layer.

## Pagination — the one thing not yet resolved

The page displays "N Potential Companions" (428 at the time this was
built). `fetch_shelter()` does a single plain GET and logs how many dog
cards it actually found versus that claimed total, so a shortfall is
visible rather than silent. Whether a live plain fetch gets all of them
or only an initial batch (with the rest loading via scroll-triggered
requests) was unverified as of the first real run — check the latest
workflow run's log for the actual numbers before assuming either way.

## Required GitHub repository secrets

Reuses the main site's FTP secrets, plus just three more:

| Secret | What it's for |
|---|---|
| `BLUEHOST_SMTP_USERNAME` | A Bluehost mailbox on the domain, e.g. `dogs@rpmhabitatconservation.org` — create one in cPanel under Email Accounts if none exists yet |
| `BLUEHOST_SMTP_PASSWORD` | That mailbox's password |
| `NOTIFY_EMAIL_TO` | Where "Ask about this dog" inquiries get sent |

The dog list alone (no inquiry form) needs none of these beyond the FTP
secrets already in use — the private directory and its path are created
and discovered automatically (see below), and `BLUEHOST_SMTP_HOST` /
`BLUEHOST_SMTP_PORT` default to this site's own domain on port 465.

All three are fully optional: if any is missing, the run does not fail —
`deploy_server_files.py` just skips writing SMTP config and logs that it
did, and `ask-about-dog.php` returns a clean "not available" response
instead of erroring. The dog list deploys either way.

Optional overrides, only needed if the defaults are ever wrong:

| Secret | Default if unset |
|---|---|
| `BLUEHOST_PRIVATE_DIR` | `topsecret_private`, created next to `public_html` if it doesn't exist |
| `BLUEHOST_SMTP_HOST` | `rpmhabitatconservation.org` |
| `BLUEHOST_SMTP_PORT` | `465` (implicit TLS/SMTPS — see the note below; 587 would use STARTTLS instead) |

Every run creates the private directory if it's missing and verifies it
actually resolves outside `public_html` — using the FTP server's own
reported absolute path, never a guess or a typed-in value — before
uploading anything there, and refuses to continue (raises, doesn't just
log a warning) if that check fails. See `ftp_sync.ensure_private_dir()`.

**Port 465 needs implicit TLS, not STARTTLS.** Bluehost's own documented
SMTP settings use port 465 with implicit TLS (SMTPS) or port 587 with
STARTTLS — never 465 with STARTTLS, which simply won't connect.
`ask-about-dog.php` picks the right one based on `SMTP_PORT`.

## Running it

- **Automatically**: `.github/workflows/topsecretproject-refresh.yml` runs
  once daily, plus whenever triggered manually from the Actions tab.
- **Locally**, for testing classifier/dataset logic without hitting the
  real site: `cd .github/pipeline && pip install -r requirements.txt`,
  then import `classifier.classify_dog()` directly with a local image
  file's bytes, or call `CACParser().parse_listing_page()` on a saved
  local HTML file instead of fetching live.

## Adding another shelter

Add an entry to the `shelters` list in `shelters_config.json` with its
own `listing_url`, `id`, and `parser`. A new shelter almost certainly
needs its own parser class in `scraper.py` (register it in `PARSERS`) —
CAC's data-attribute structure is specific to the PetMatchPro plugin, not
something to assume other shelters share.

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
`BC-0142` — find it on a dog's card, or in workflow run logs' per-breed
counts, which name codes but never names/IDs/URLs):

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

Bluehost FTP / SMTP passwords: change them in cPanel, update the matching
GitHub secret. Next run picks it up automatically.

## Known gaps / things not verified in this environment

- Pagination (see above) — depends on the first real workflow run's logs.
- The classifier model (`resnet50.a1_in1k` via timm) was verified for
  correct label strings and filter behavior, but full inference couldn't
  be tested in the environment this was built in, because that sandbox
  couldn't reach Hugging Face Hub (where timm downloads pretrained
  weights from) — a normal GitHub Actions runner has unrestricted
  internet access and won't hit this.
