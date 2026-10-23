# Deploying the nextecon.org archive

What's left after this repo is pushed to `github.com/benjaminbradley/nextecon`.
The site is in `docs/`, and `docs/CNAME` already says `nextecon.org`.

## 1. Push

```sh
cd archive
git push -u origin main
```

## 2. Turn on GitHub Pages

Repo → **Settings → Pages**:

1. **Source:** *Deploy from a branch*
2. **Branch:** `main`, folder `/docs` → **Save**
3. **Custom domain:** should show `nextecon.org` (read from `docs/CNAME`). If it's empty, type `nextecon.org` and save.
4. Leave **Enforce HTTPS** for now. It becomes available after DNS works (step 4).

Check the deploy: open the **Actions** tab and look for a green "pages build and deployment" run. Until DNS points at GitHub, you can preview the site at
`https://benjaminbradley.github.io/nextecon/`. That preview works only because every link in the archive is relative.

## 3. (Recommended) Verify the domain with GitHub

Account → **Settings → Pages → Add a domain** → `nextecon.org`. GitHub gives you a TXT record (`_github-pages-challenge-benjaminbradley.nextecon.org`). Add it at your DNS provider, then click **Verify**. This stops anyone else's repo from claiming your domain.

## 4. Point DNS at GitHub

At your DNS provider for `nextecon.org`:

**Before changing anything:**
- A day ahead, lower the TTL on the existing records (for example to 300 s) so the switch takes effect quickly.
- Keep a copy of the current records in case you need to roll back.
- Don't touch MX/email records.

**Remove** the existing `A`/`AAAA` records for `nextecon.org` (and `www`) that point at the old WordPress host.

**Add:**

| Type  | Name  | Value                          |
|-------|-------|--------------------------------|
| A     | @     | 185.199.108.153                |
| A     | @     | 185.199.109.153                |
| A     | @     | 185.199.110.153                |
| A     | @     | 185.199.111.153                |
| AAAA  | @     | 2606:50c0:8000::153            |
| AAAA  | @     | 2606:50c0:8001::153            |
| AAAA  | @     | 2606:50c0:8002::153            |
| AAAA  | @     | 2606:50c0:8003::153            |
| CNAME | www   | benjaminbradley.github.io.     |

With the `www` CNAME in place, GitHub redirects `www.nextecon.org` to `nextecon.org` automatically.

If the domain has **CAA** records, one of them must allow `letsencrypt.org`. Otherwise GitHub can't issue the HTTPS certificate.

Check propagation:

```sh
dig +short nextecon.org A
dig +short www.nextecon.org CNAME
```

## 5. Turn on HTTPS

Once DNS resolves to GitHub, go back to **Settings → Pages**. The DNS check should go green, and GitHub requests a Let's Encrypt certificate, which can take from a few minutes up to about an hour. Then tick **Enforce HTTPS**.

If the certificate seems stuck, clear the Custom domain field, save, re-enter `nextecon.org`, and save again.

## 6. Afterwards

- Click through the live site and compare it with the old one. Old URLs (`/schedule/`, `/speaker-bios/`, …) keep the same paths.
- **Before you shut down the WordPress host**, take a final backup: a database dump plus `wp-content/`. Back up the whole uploads folder too. Some files in it aren't in this archive.
- Cancel the old hosting only once the new site has run fine for a while.
