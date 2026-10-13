# RPM Habitat Conservation — project brief

This is the brief that shaped this site. Keep it in the project root so future
edits stay consistent with the same facts and constraints — do not add facts
that aren't in here, and don't undo the omissions (litigation, donations,
volunteer signup, parcel/deed/address details) without explicit sign-off from
the site owner.

---

Claude Code brief — RPM Habitat Conservation website
Paste this whole file into Claude Code (or save it as `CLAUDE.md` in the project root). Items marked [CONFIRM] are placeholders I could not verify — fill or delete them before the site goes live. Do not invent values for them.

## What I need built

A small, fast, static marketing/informational site for RPM Habitat Conservation, LLC, replacing a prior site at `rpmhabitatconservation.org` that is no longer up. Static HTML/CSS with minimal JS. No CMS, no build step unless you have a strong reason. It must work on a cheap host or GitHub Pages / Netlify / Cloudflare Pages. It is however currently hosted on Bluehost.

## Who the organization is

RPM Habitat Conservation, LLC is an Ohio limited liability company — not a 501(c)(3) nonprofit. It is based in Cincinnati, Ohio. [Registered street address redacted from this repo file per owner request (2026-10-13) — this repo is public; keep the address out-of-band and do not add it back here or to the site.]

Its purpose is to acquire, hold, and restore ecologically significant land in the Ohio River hill country of southwestern Ohio, and to keep it out of development. It is a working conservation property, not a membership organization or a public charity.

## The land

* Size: ~7.25 acres [CONFIRM — still unresolved as of 2026-10-13. If 7.25 is a combined figure across two adjoining parcels, say "roughly 7 acres across two adjoining parcels"; if it's a corrected survey figure for the single tract, use it as-is. Parcel number and legal description redacted from this repo file per owner request — do not add them back here or to the site.]
* Where: Miami Township, Hamilton County, Ohio. [Street address / legal description redacted from this repo file per owner request (2026-10-13) — this repo is public; keep that detail out-of-band.]
* How it was acquired: [Acquisition narrative redacted from this repo file per owner request (2026-10-13). The site no longer publishes acquisition details (how/when the tract was obtained) at all — do not add any version of that narrative back to the site or this file without explicit sign-off.]
* Terrain: steep wooded hillside in the Kope Formation (interbedded shale and limestone), running down to the confluence of two creeks at the low point of the tract.
* Why it matters ecologically: mature forest canopy; riparian corridor at a two-creek confluence; part of the Ohio River hillside forest system.
* Notable plantings: the tract holds Torreya taxifolia (Florida torreya), American chestnut (Castanea dentata), and buffalo clover (Trifolium stoloniferum, running buffalo clover) — none of these are naturally occurring populations on this site. Do not publish specific locations, counts, or directions. One sentence acknowledging presence per species is fine; a map is not.

## What the organization actually does

As of the 2026-10-13 formal revision, the site describes this in institutional, third-person terms. Current framing (see `stewardship.html`):

1. Holds the land. Keeps the tract in private conservation ownership.
2. Manages with minimal intervention. The forest is protected and left to grow on its own terms; the tract is not developed, not open to the public, and not offered for recreation or events.
3. Conserves rare plants. Torreya taxifolia, American chestnut, and running buffalo clover are conserved on the property and looked after over time.

Superseded framing (kept here only as historical record — do not restore without explicit sign-off): earlier copy described an active "small container nursery" doing native-plant propagation and reforestation, with seasonal planting work. The owner asked to remove all of that language (nursery/propagation/reforestation) in favor of the minimal-intervention framing above.

## External links / further reading

As of the 2026-10-13 revision, the owner asked to remove all external links and any "further reading" / "allies" section from the site entirely. Do not add links to Cardinal Land Conservancy, The Hillside Trust, the Hamilton County Conservation District, Torreya Guardians, or any other organization without explicit sign-off — current tone is formal/institutional and doesn't reference peer organizations.

## Do not put on the site

* Anything about adjoining-property disputes, pending or contemplated litigation, or regulatory filings. A public website (and this public repo) is discoverable and will be read by opposing counsel. If the site needs a reason the land is worth protecting, the ecology stands on its own. [2026-10-13: do not name the specific type of dispute in this file either — naming it here, in a public repo, is itself a disclosure.]
* Any "Donate" button or donation language. This is an LLC; contributions are not tax-deductible and soliciting them as if they were creates real exposure. If the owner later wants to accept money, the correct answer is either a fiscal sponsor or a separate 501(c)(3), not a Stripe button on an LLC site.
* Any "Volunteer" signup that implies organized public access. Liability argues against it.
* Parcel numbers, deed book/page references, the registered address, and acquisition/purchase details (how or when the tract was obtained, or any price) — none of these belong in this repo's current files, including this one.
* As of 2026-10-13: the words "nonprofit," "charity," "foundation," "preserve," "nature preserve," or "tax-exempt" to describe the organization — it is a privately held LLC. Never say the land is protected "forever" or "in perpetuity." Never mention a conservation easement.

## Pages

Keep it to four. This is a small operation and a six-page nonprofit template will read as padding.

1. Home — what the tract is, where it is (region, not address), why hillside forest matters here. One strong image.
2. The Land — as of 2026-10-13: Bedrock, History (Miami Purchase / Hamilton County founding), Forest, and Rare plants (`#plants`, three species: torreya, chestnut, running buffalo clover). This is the substantive page. No external links.
3. Stewardship — as of 2026-10-13: Approach (minimal intervention), Rare plant conservation, Long-term ownership. No nursery/propagation/reforestation language.
4. Contact — an email address only. [CONFIRM — no address supplied yet. Do not use a personal cell number or the residential registered address.]

## Design direction

* Ground the design in Ohio River hillside forest and Kope shale, not in generic "green nonprofit." Reference palette: wet shale grey, limestone buff, winter oak brown, creek-water slate, one restrained living green. Avoid a cream-and-terracotta palette and avoid the stacked rounded-card layout — both read as template.
* One or two typefaces, no more. Type should feel steady and a little geological. No all-caps eyebrow labels above headings, no single-word color accents in headlines, no "→" glued to button text.
* Spend the boldness in one place: the hero. The most characteristic thing about this land is the steep drop to the creek confluence — a single strong full-width photograph, or a simple cross-section/elevation treatment of the hillside, beats a stat block.
* Real photographs of the actual tract are strongly preferred over stock. [CONFIRM — owner will supply images; use clearly-labeled placeholders sized to the layout until then.]
* Quality floor without announcing it: responsive to mobile, visible keyboard focus, reduced motion respected, accessible contrast, semantic HTML, sensible `<title>`/meta description per page, and an OG image.

## Copy rules

* As of the 2026-10-13 formal revision, tone is **formal, institutional, third person, understated** — this supersedes the original landowner-voice direction below.
* ~~Write it as a landowner describing their land, not as an institution describing its programs.~~ (superseded 2026-10-13)
* Plain sentences, active voice, no mission-statement register, no "we are committed to."
* Never state a species, acreage, elevation, or date that isn't given directly by the owner. If a fact isn't given, leave a visible `TODO:` in the HTML rather than filling it in.
* Never call the organization a nonprofit, charity, foundation, preserve, nature preserve, or tax-exempt. Never say the land is protected "forever" or "in perpetuity." Never mention a conservation easement.

## Deliverables

* `index.html`, `land.html`, `stewardship.html`, `contact.html`, one shared stylesheet, one small JS file only if genuinely needed.
* A short `README.md` with deploy instructions.
* Before writing code: give the owner a compact design plan — 4–6 named hex values, the typefaces and their roles, and an ASCII wireframe of the home page — and wait for go-ahead.

---

## Open TODOs before launch

- [ ] Confirm exact acreage / parcel structure (see [CONFIRM] above) — `land.html` currently says "roughly seven acres" with an HTML comment flagging this.
- [ ] Supply a real contact email — `contact.html` currently has a visible `TODO: insert contact email` placeholder / `mailto:TODO-INSERT-EMAIL@example.com`.
- [ ] Supply real photographs — `land.html` (#plants: one per species) and `stewardship.html` still have labeled placeholder blocks as of 2026-10-13 (no usable photos received that round). Ideally also replace the hero illustration (`assets/img/hillside-hero.svg`) with a real photo if one fits.
- [ ] Replace `assets/img/og-image.png` (currently a generated placeholder banded in the site's palette) with a real social-share image once photography exists.
- [x] Deploy target: resolved. Bluehost auto-deploy via GitHub Actions (`.github/workflows/deploy.yml`) is live and confirmed working; document root is `public_html` (see README.md).
- [x] Buffalo clover species: resolved 2026-10-13. Owner confirmed it's running buffalo clover, *Trifolium stoloniferum*.

## Amendments after initial build

- The owner asked to add two more notable species to the Land page, alongside the torreya: American chestnut (*Castanea dentata*) and buffalo clover. Added to `land.html` under "Rare and notable plants," following the same no-locations/no-counts restraint as the torreya paragraph.
- The owner asked to remove "landslide" and "unstable"-hillside framing from public-facing copy (legal/liability concern — that language could work against the owner if read adversarially). Removed from `index.html` and `land.html`.
- **2026-10-13 — major formal revision.** The owner requested a full tone and content rewrite: formal/institutional/third-person voice; the organization is never called a nonprofit, charity, foundation, preserve, or tax-exempt, and the land is never described as protected "forever"/"in perpetuity," with no mention of a conservation easement. Content changes: `land.html` restructured to Bedrock / History (new — Miami Purchase, Hamilton County founding) / Forest / Rare plants (`#plants`, three species, each with its own sub-heading); all external links and the "Further reading" section removed from `land.html`. `stewardship.html` restructured to Approach / Rare plant conservation / Long-term ownership, with all nursery/propagation/reforestation/seasonal-work/assisted-migration/Torreya Guardians language removed. `contact.html` rewritten to state plainly it's not a nonprofit and does not solicit contributions or memberships. Footer on every page changed to "© 2026 RPM Habitat Conservation, LLC · Private property. No public access." The owner's registered address, parcel number, legal description, and acquisition/purchase narrative were redacted from this file itself (see above) since this repo is public on GitHub — do not add any of that back here or to the site without explicit sign-off.
