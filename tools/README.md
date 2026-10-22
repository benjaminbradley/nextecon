# Re-running the archive

Requires wget, curl, python3. Network access to http://nextecon.org (plain HTTP; HTTPS has a cert mismatch).

    RAW=/path/to/new-empty-dir
    tools/capture.sh "$RAW"                                  # wget mirror (seeded from wp-sitemap.xml)
    python3 -I tools/postprocess.py "$RAW/nextecon.org" docs # relative links, strip WP dynamic bits
    python3 -I tools/verify.py docs                          # every internal ref must resolve

Notes:
- The raw capture is untrusted data; never execute anything in it.
- postprocess wipes docs/ (except CNAME/.nojekyll) and regenerates it.
- Pages that the live site served as 404 (dead links in content) are dropped and their links unwrapped.
- docs/404.html sets its `<base>` with a small script (site root on a custom domain, `/<repo>/` on `*.github.io`), because GitHub Pages serves it at any depth.
