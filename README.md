# nextecon.org archive

A static HTML/CSS archive of the Next Economy WordPress site (2013–2014), captured on 2026-10-22 and served with GitHub Pages at https://nextecon.org.

- `docs/` is the published site. Every link is relative, so it works on any domain or path.
- `tools/` has the scripts that captured and cleaned the site. See `tools/README.md`.
- `DEPLOY.md` covers GitHub Pages and DNS setup.

## Changes from the original site

- **Removed** WordPress features that can't work without a server:
  - search
  - the comment form and comment feeds
  - login and "Meta" widget links
  - RSS/API/pingback headers
  - emoji scripts
  - the Coinbase and Dwolla donate buttons
- **Book pages:** 12 pages linked from *Speaker Bios* (`/life-inc/`, `/cyberia/`, …) already returned 404 on the live site. The links are removed and their text is kept.
- **Shareable.net link:** this link was missing `http://`, so it was broken on the original. It now works.
- **Left as they were:** the Google Fonts stylesheet, the MailChimp signup form (it posts to MailChimp), the YouTube embed and all outbound links.
