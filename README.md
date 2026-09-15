# RPM Habitat Conservation

Static site for RPM Habitat Conservation, LLC. Plain HTML/CSS, no build step,
no framework, one shared stylesheet (`styles.css`).

## Structure

```
index.html          Home
land.html           The Land
stewardship.html    Stewardship
contact.html        Contact
styles.css          Shared stylesheet
assets/img/         Hero illustration + OG image (placeholders — see CLAUDE.md TODOs)
```

## Before this goes live

See the "Open TODOs before launch" section at the bottom of `CLAUDE.md` —
contact email, exact acreage wording, and real photography all need the
owner's input before publishing.

## Local preview

No build step. Either open `index.html` directly in a browser, or serve the
folder so absolute paths (`/land.html`, `/assets/...`) resolve correctly:

```
python3 -m http.server 8000
# then visit http://localhost:8000
```

## Deploy

The site is plain static files, so any of the following work with no changes:

### GitHub Pages

1. Push this repo to GitHub (already done if you're reading this from the repo).
2. In the repo settings, under **Pages**, set the source to the `main` branch, root folder.
3. GitHub serves the site at `https://<user>.github.io/<repo>/`. For a custom
   domain, add a `CNAME` file containing the domain and point the domain's DNS
   at GitHub Pages per [GitHub's custom domain docs](https://docs.github.com/pages/configuring-a-custom-domain-for-your-github-pages-site).

### Netlify / Cloudflare Pages

1. Connect the repo.
2. Build command: none. Publish directory: `/` (repo root).
3. Point your domain at the generated Netlify/Cloudflare site.

### Bluehost (current host)

Upload the contents of this repo (all files, preserving the `assets/` folder)
to `public_html/` (or the relevant document root) via the Bluehost file
manager or SFTP. No server-side processing is required — it's static files.

## Editing

Each page repeats the same header/nav/footer markup (no templating layer, by
design — see `CLAUDE.md` for why: no CMS, no build step). If you add a page,
copy the structure of an existing one and update the nav's `aria-current`
attribute to match.
