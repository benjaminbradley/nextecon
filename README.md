# nextecon.org archive

A static HTML/CSS archive of the Next Economy WordPress site (2013–2014), captured on 2026-10-22 and served with GitHub Pages at https://nextecon.org.

- `docs/` is the published site. Every link is relative, so it works on any domain or path.
- `DEPLOY.md` covers GitHub Pages and DNS setup.

## How it was made

The site was downloaded with wget (all pages listed in its sitemaps, plus the images, CSS and JS they use), cleaned of WordPress features that need a server, rewritten so every link is relative, and checked: every internal link was confirmed to work, and page text was compared against the original.

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
- **Footer:** "Proudly powered by WordPress" now reads "No longer powered by WordPress" (not a link).
- **Left as they were:** the Google Fonts stylesheet, the MailChimp signup form (it posts to MailChimp), the YouTube embed and all outbound links.
