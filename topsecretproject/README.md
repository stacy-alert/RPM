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

**Live fetching is currently blocked.** On 2026-11-16, CAC's site
returned HTTP 403 to the GitHub Actions runner (likely IP/ASN-level bot
protection, not something polite request behavior can fix). Per owner
instruction, the pipeline did not attempt to work around this. It
currently reads from a saved HTML snapshot instead — see below — and the
public page is labeled "Data as of [snapshot date]" so it's clear it
isn't live.

**Public data now includes name, CAC ID, and listing link.** Also on
2026-11-16, and specifically *because* the email inquiry form isn't
configured, the owner decided `dogs.json` should carry each dog's name,
`shelter_seq_id` (CAC's own public sequential ID), and `listing_url`, so
cards can show "View at Cincinnati Animal CARE" directly. This is a
deliberate reversal of this project's original minimal-disclosure
design — see `dataset.py`'s module docstring for exactly what changed
and why, including the accepted ToS risk (CAC's Terms of Use prohibit
both republishing their content and hyperlinking to their site, each
under its own $100k liquidated-damages clause). The AnimalsFirst
internal `cac_id` is still never made public — only `lookup.json`
(private) carries it.

**Photos are now downloaded and hosted ourselves.** On 2026-11-20 the
owner asked for one photo per dog on the public page, fetched and
re-hosted under our own domain rather than hotlinked from the shelter's
own copy. This is a further step past the 2026-11-16 decision above —
not just text data but an actual copy of the shelter's photo, which is
the most direct form of the ToS's no-republish risk this project has
taken on. `main.py` fetches `photo_urls[0]` for each *published* dog
(after breed matching, so the great majority of scraped dogs are never
fetched at all), uploads it to `topsecretproject/photos/<reference
code>.<ext>`, and sets that as `dogs.json`'s `photo_url` for that dog —
never the original shelter/S3 URL. If the fetch or upload fails for any
reason, `photo_url` stays `null` and the page shows a placeholder
instead; there is no hotlinking fallback. See `main.py`'s
`_photo_extension()`/photo-hosting block and `ftp_sync.upload_binary()`/
`ensure_dir()`.

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

## Saved-snapshot data source (while CAC blocks the runner)

`fetch_shelter()` in `scraper.py` supports two modes per shelter, picked
by `shelters_config.json`'s `"source"` field:

- `"live"` (default if unset): fetch the real URL, exactly as before.
- `"snapshot"`: read a local HTML file (`"snapshot_path"`, relative to
  `.github/pipeline/`) instead of touching CAC's site at all. Requires
  `"snapshot_date"` (a human-readable string, e.g. `"November 2026"` or
  an exact date) — this flows straight into `dogs.json`'s `data_as_of`
  field and the page's "Data as of ..." banner.

Photo downloads are unaffected either way — they always go straight to
AnimalsFirst's S3 addresses, which is a separate question from whether
the *listing* page itself came from a live fetch or a saved file. If S3
ever blocks the runner too, that's a new, separate stop-and-report case.

The saved HTML file is committed to the repo under
`.github/pipeline/fixtures/` — normally CAC's identifying data would
never be committed (see the main privacy design), but this is a single
point-in-time snapshot the owner explicitly approved committing, since
the same information is now published in `dogs.json` anyway (see above).

To switch a shelter back to live once/if CAC's block lifts, just change
its `"source"` back to `"live"` (or remove the key) in
`shelters_config.json` — no code change needed.

## Pagination — unresolved, moot while in snapshot mode

The live page displays "N Potential Companions" (428 as of October
2026). `fetch_shelter()`'s live-fetch path does a single plain GET and
logs how many dog cards it actually found versus that claimed total, so
a shortfall would be visible rather than silent — but this has never
been exercised against the real site, since every live attempt either
failed on missing secrets or hit the 403 block above. Revisit this once
live fetching is possible again.

## Why the hourly schedule alone runs hours late, and the fix

GitHub's `schedule` trigger is not reliable at hourly frequency. Pulling
the actual `created_at` timestamps of this workflow's `schedule`-triggered
runs (2026-11-17 through 2026-11-21) shows gaps of 5-10 hours between
runs, not the ~1 hour the cron expression (`23 * * * *`) asks for —
GitHub's own docs say scheduled workflows "can be delayed during periods
of high load" and runs may be dropped outright, and in practice this repo
sees far fewer firings than requested. No cron-offset tweak fixes this;
the trigger itself just doesn't run on time.

The real fix (2026-11-21): `upload.php` calls GitHub's API to fire
`workflow_dispatch` on this workflow directly, the moment `cac_raw.json`
is saved — seconds after the Pi's (or a manual bookmark's) upload
finishes, instead of waiting on GitHub's own unreliable poll.
`check_new_data.py` already processes unconditionally on
`workflow_dispatch`, so no gating logic needed to change. The hourly
`schedule` stays in place as a fallback in case the direct call ever
fails (expired token, GitHub API hiccup) — belt and suspenders, not
either/or.

## Required GitHub repository secrets

Reuses the main site's FTP secrets, plus just three more:

| Secret | What it's for |
|---|---|
| `BLUEHOST_SMTP_USERNAME` | A Bluehost mailbox on the domain, e.g. `dogs@rpmhabitatconservation.org` — create one in cPanel under Email Accounts if none exists yet |
| `BLUEHOST_SMTP_PASSWORD` | That mailbox's password |
| `NOTIFY_EMAIL_TO` | Where "Ask about this dog" inquiries get sent |
| `GH_DISPATCH_TOKEN` | Optional. A GitHub token so `upload.php` can trigger this workflow immediately on upload (see above) instead of relying solely on the hourly schedule. Create a fine-grained personal access token (Settings → Developer settings → Personal access tokens → Fine-grained tokens) scoped to **only this repository**, with repository permission **Actions: Read and write**, nothing else. Without it, the dog list still updates — just only whenever GitHub's hourly schedule actually fires. Note: can't be named `GITHUB_*` — GitHub reserves that prefix for its own secrets, which is why this one is `GH_DISPATCH_TOKEN`. |

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
