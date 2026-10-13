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

RPM Habitat Conservation, LLC is an Ohio limited liability company — not a 501(c)(3) nonprofit. It is a single-owner conservation landholding entity based in Cincinnati, Ohio (registered address 7340 Southpointe Drive, Cincinnati, OH 45233).

Its purpose is to acquire, hold, and restore ecologically significant land in the Ohio River hill country of southwestern Ohio, and to keep it out of development. It is a working conservation property, not a membership organization or a public charity.

## The land

* Size: ~7.25 acres [CONFIRM — my records from prior work show the Green Belt Tract as 7.0000 acres for Hamilton County Auditor parcel 570-0170-0175-00, plus a separate adjoining access parcel. If 7.25 is the combined figure, say "roughly 7 acres across two adjoining parcels"; if 7.25 is a corrected survey figure for the tract, use it.]
* Where: Mt. Nebo Road, Section 20, Town 1, Fractional Range 2, Miami Township, Hamilton County, Ohio. Sometimes referenced in records as "SS Brunsman Way (Rear)." Described in the subdivision plat record as a "Green Belt Tract."
* How it was acquired: at a Hamilton County tax-forfeited land sale in September 2025, after the parcel forfeited to the State of Ohio. Deed recorded November 2025. (Frame this as rescue of an abandoned, forfeited parcel — that's the true and compelling version. Do not publish the purchase price.)
* Terrain: steep wooded hillside in the Kope Formation (interbedded shale and limestone — notoriously landslide-prone), running down to the confluence of two creeks at the low point of the tract.
* Why it matters ecologically: mature forest canopy doing real hydrologic and slope-stability work on an unstable hillside; riparian corridor at a two-creek confluence; part of the Ohio River hillside system that the region's hillside-protection groups have worked to keep forested.
* Notable plantings: the tract holds mature specimens of Torreya taxifolia (Florida torreya), a federally endangered conifer, growing well north of its native Gulf Coast range. Do not publish specific locations, counts, or directions. One sentence acknowledging their presence is fine; a map is not.

## What the organization actually does

Three real activities. Write the site around these, not around generic conservation language:

1. Hold and protect the land. Keeping a forfeited hillside tract in conservation ownership rather than letting it return to the development cycle.
2. Reforestation and native plant propagation. A small container nursery operation focused on native stock, with plantings going back onto the tract.
3. Rare conifer stewardship. Maintaining the existing torreya specimens as part of the assisted-migration conversation around that species.

## Peer organizations (for an "allies / further reading" section, if you build one)

Cardinal Land Conservancy, The Hillside Trust, Hamilton County Soil & Water Conservation District (now the Hamilton County Conservation District), Torreya Guardians. Link out; do not claim partnership, affiliation, or endorsement by any of them unless told a partnership exists.

## Do not put on the site

* Anything about the easement dispute, the adjoining development, the developer, pending or contemplated litigation, or regulatory filings. A public website is discoverable and will be read by opposing counsel. If the site needs a reason the land is worth protecting, the ecology and the slope stand on their own.
* Any "Donate" button or donation language. This is an LLC; contributions are not tax-deductible and soliciting them as if they were creates real exposure. If the owner later wants to accept money, the correct answer is either a fiscal sponsor or a separate 501(c)(3), not a Stripe button on an LLC site.
* Any "Volunteer" signup that implies organized public access to a steep, unstable hillside. Liability and slope conditions both argue against it.
* Parcel numbers, deed book/page references, and the site address as a visit-here location.

## Pages

Keep it to four. This is a small operation and a six-page nonprofit template will read as padding.

1. Home — what the tract is, where it is (region, not address), why hillside forest matters here. One strong image.
2. The Land — geology, hydrology, forest, the two-creek confluence, the torreya specimens. This is the substantive page.
3. Stewardship — reforestation, native propagation, what the work actually looks like season to season.
4. Contact — an email address only. [CONFIRM — no address supplied yet. Do not use a personal cell number or the residential registered address.]

## Design direction

* Ground the design in Ohio River hillside forest and Kope shale, not in generic "green nonprofit." Reference palette: wet shale grey, limestone buff, winter oak brown, creek-water slate, one restrained living green. Avoid a cream-and-terracotta palette and avoid the stacked rounded-card layout — both read as template.
* One or two typefaces, no more. Type should feel steady and a little geological. No all-caps eyebrow labels above headings, no single-word color accents in headlines, no "→" glued to button text.
* Spend the boldness in one place: the hero. The most characteristic thing about this land is the steep drop to the creek confluence — a single strong full-width photograph, or a simple cross-section/elevation treatment of the hillside, beats a stat block.
* Real photographs of the actual tract are strongly preferred over stock. [CONFIRM — owner will supply images; use clearly-labeled placeholders sized to the layout until then.]
* Quality floor without announcing it: responsive to mobile, visible keyboard focus, reduced motion respected, accessible contrast, semantic HTML, sensible `<title>`/meta description per page, and an OG image.

## Copy rules

* Plain sentences, active voice, no mission-statement register, no "we are committed to."
* Write it as a landowner describing their land, not as an institution describing its programs.
* Never state a species, acreage, elevation, or date that isn't in this brief. If a fact isn't given, leave a visible `TODO:` in the HTML rather than filling it in.

## Deliverables

* `index.html`, `land.html`, `stewardship.html`, `contact.html`, one shared stylesheet, one small JS file only if genuinely needed.
* A short `README.md` with deploy instructions.
* Before writing code: give the owner a compact design plan — 4–6 named hex values, the typefaces and their roles, and an ASCII wireframe of the home page — and wait for go-ahead.

---

## Open TODOs before launch

- [ ] Confirm exact acreage / parcel structure (see [CONFIRM] above) — `land.html` currently says "roughly seven acres" with an HTML comment flagging this.
- [ ] Supply a real contact email — `contact.html` and `index.html` currently have a visible `TODO: insert contact email` placeholder / `mailto:TODO-INSERT-EMAIL@example.com`.
- [ ] Supply real photographs to replace the labeled placeholder blocks on `land.html` and `stewardship.html`, and ideally replace the hero illustration (`assets/img/hillside-hero.svg`) with a real photo of the confluence if one becomes available.
- [ ] Replace `assets/img/og-image.png` (currently a generated placeholder banded in the site's palette) with a real social-share image once photography exists.
- [ ] Decide on and configure the actual deploy target (GitHub Pages / Netlify / Cloudflare Pages / Bluehost) — see `README.md`.
- [ ] Confirm the exact buffalo clover species (`Trifolium reflexum`, or `Trifolium stoloniferum` / "running buffalo clover") and its current listing status — see the TODO comment in `land.html`. Note: running buffalo clover was delisted from the federal endangered species list in 2021 after recovery, so "endangered" should not be asserted for it without confirming that's actually the species present.

## Amendments after initial build

- The owner asked to add two more notable species to the Land page, alongside the torreya: American chestnut (*Castanea dentata*) and buffalo clover. Added to `land.html` under "Rare and notable plants," following the same no-locations/no-counts restraint as the torreya paragraph.
- The owner asked to remove "landslide" and "unstable"-hillside framing from public-facing copy (legal/liability concern — that language could work against the owner if read adversarially). Removed from `index.html` and `land.html`. The geology and forest sections now describe the slope as steep and the canopy's erosion-control role without asserting landslide risk or instability. The original brief text above (which used that framing) is left as-is as a historical record of the initial brief — it is not current public copy.
