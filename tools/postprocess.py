#!/usr/bin/env python3
"""Turn a raw wget mirror of nextecon.org into a static, relative-link site.

usage: python3 -I postprocess.py RAW_DIR/nextecon.org OUT_DOCS_DIR
"""
import html, os, posixpath, re, shutil, sys
from urllib.parse import urlsplit

SRC, OUT = sys.argv[1], sys.argv[2]
DATE = "2026-10-22"
HOSTS = {"nextecon.org", "www.nextecon.org"}
log = {"broken": [], "collisions": [], "removed": {}, "fixed_relative_external": []}

def bump(k, n=1):
    log["removed"][k] = log["removed"].get(k, 0) + n

# ---------------------------------------------------------------- file map
SKIP_PREFIXES = ("www.shareable.net/",)   # wget artefact of a broken relative link in the content
files = {}   # site path (no leading /) -> raw abs path
for root, _, names in os.walk(SRC):
    for n in names:
        raw = os.path.join(root, n)
        rel = os.path.relpath(raw, SRC).replace(os.sep, "/")
        if rel.startswith(SKIP_PREFIXES) or "/www.shareable.net/" in rel:
            continue
        clean = rel.split("?", 1)[0]
        if clean in files:
            # prefer the unqueried capture; otherwise keep first and log
            if "?" in rel:
                log["collisions"].append((rel, clean))
                continue
            log["collisions"].append((files[clean], clean))
        files[clean] = raw

pages = {}   # dir path ('' for root) -> output file rel path
assets = {}  # site path -> out path
for p in files:
    if p.endswith("/index.html") or p == "index.html":
        d = p[: -len("index.html")].rstrip("/")
        if d == "this-page-does-not-exist-404":
            pages[d] = "404.html"
        else:
            pages[d] = p
    else:
        assets[p] = p
# pages the original site served as 404 (dead links in the content): drop them, unwrap links to them
dead = set()
for d in list(pages):
    if d == "this-page-does-not-exist-404":
        continue
    with open(files[("%s/index.html" % d) if d else "index.html"], encoding="utf-8", errors="replace") as f:
        if re.search(r'<body class="[^"]*\berror404\b', f.read(4000 + 60000)):
            dead.add(d)
            del pages[d]
log["dead"] = sorted(dead)
outpaths = set(pages.values()) | set(assets.values())
dirs_with_page = {d for d in pages if d != "this-page-does-not-exist-404"}

# ---------------------------------------------------------------- URL rewriting
def rel_to(page_dir, target):
    r = posixpath.relpath(target or ".", page_dir or ".")
    return r

def rewrite_url(url, page_dir, ctx):
    """Return rewritten url (unescaped form) or None if unchanged."""
    u = url.strip()
    if not u or u[0] == "#" or re.match(r"(mailto|tel|data|javascript|sms):", u, re.I):
        return None
    path = None
    if u.startswith("//"):
        sp = urlsplit("http:" + u)
        if sp.hostname in HOSTS:
            path = sp.path
        else:
            return None
        q, frag = "", sp.fragment
    elif re.match(r"https?://", u, re.I):
        sp = urlsplit(u)
        if (sp.hostname or "") in HOSTS:
            path, frag = sp.path, sp.fragment
        else:
            return None
    elif u.startswith("/"):
        sp = urlsplit(u)
        path, frag = sp.path, sp.fragment
    else:
        if re.match(r"www\.[a-z0-9-]+\.[a-z]{2,}(/|$)", u, re.I):
            log["fixed_relative_external"].append((ctx, u))
            return "http://" + u
        sp = urlsplit(u)
        path, frag = sp.path, sp.fragment
        path = posixpath.normpath(posixpath.join("/" + page_dir, path)) if path else "/" + page_dir
        if sp.path.endswith("/") and not path.endswith("/"):
            path += "/"
    path = posixpath.normpath(path) if path else "/"
    p = path.lstrip("/")
    f = ("#" + frag) if frag else ""
    if p in ("", "."):
        return (rel_to(page_dir, "") + "/").replace("./", "./", 1) .replace("//", "/") + f if page_dir else "./" + f
    if p in assets:
        return rel_to(page_dir, p) + f
    d = p.rstrip("/")
    if d in dirs_with_page:
        return rel_to(page_dir, d) + "/" + f
    if d in dead:
        return "\0DEAD"
    log["broken"].append((ctx, url))
    return rel_to(page_dir, p) + f

def esc(s):
    return s.replace("&", "&amp;").replace('"', "&quot;")

ATTR = re.compile(r"""(\s(?:href|src|srcset|action|poster|data-src|data-redirect)\s*=\s*)(["'])(.*?)\2""", re.I | re.S)

def fix_attr(m, page_dir, ctx):
    name, q, val = m.group(1), m.group(2), m.group(3)
    v = html.unescape(val)
    if name.strip().lower().startswith("srcset"):
        parts = []
        changed = False
        for ent in re.split(r",\s+|,(?=/|http)", v.strip()):
            bits = ent.strip().split(None, 1)
            if not bits:
                continue
            nu = rewrite_url(bits[0], page_dir, ctx)
            changed |= nu is not None
            parts.append((nu or bits[0]) + ((" " + bits[1]) if len(bits) > 1 else ""))
        if not changed:
            return m.group(0)
        return name + q + esc(", ".join(parts)) + q
    nu = rewrite_url(v, page_dir, ctx)
    if nu is None:
        return m.group(0)
    if nu == "\0DEAD":
        return name + q + "\0DEAD" + q
    return name + q + esc(nu) + q

CSSURL = re.compile(r"""url\(\s*(["']?)(.*?)\1\s*\)""", re.S)
def fix_css(text, base_dir, ctx, strip_query=True):
    def r(m):
        u = html.unescape(m.group(2)) if "&" in m.group(2) else m.group(2)
        nu = rewrite_url(u, base_dir, ctx)
        if nu is None:
            # relative within CSS: strip query (we stripped it from filenames)
            if strip_query and not re.match(r"(https?:|//|data:|#)", u):
                nu = re.split(r"[?#]", u, 1)[0]
                if nu == u:
                    return m.group(0)
            else:
                return m.group(0)
        return "url(" + m.group(1) + nu + m.group(1) + ")"
    return CSSURL.sub(r, text)

# ---------------------------------------------------------------- HTML cleanup
def drop(pattern, s, key, flags=re.S | re.I):
    s, n = re.subn(pattern, "", s, flags=flags)
    if n:
        bump(key, n)
    return s

def clean_html(s):
    # IE html5 shim conditional (file not captured)
    s = drop(r"<!--\[if lt IE 9\]>.*?<!\[endif\]-->\s*", s, "IE html5.js shim")
    # link tags
    def linkfilter(m):
        t = m.group(0)
        rel = re.search(r"""rel\s*=\s*["']([^"']*)["']""", t, re.I)
        rel = rel.group(1).lower() if rel else ""
        href = re.search(r"""href\s*=\s*["']([^"']*)["']""", t, re.I)
        href = href.group(1) if href else ""
        if rel in ("alternate", "editURI".lower(), "https://api.w.org/", "shortlink", "canonical",
                   "pingback", "wlwmanifest") or "oembed" in t.lower() or \
           (rel == "dns-prefetch" and "s.w.org" in href):
            bump("<link rel=%s>" % (rel.split()[0] if rel else "?"))
            return ""
        return t
    s = re.sub(r"<link\b[^>]*>\s*", linkfilter, s, flags=re.I)
    s = drop(r"<meta\s+(?:property|name)\s*=\s*[\"'](?:og:|twitter:|generator)[^>]*>\s*", s, "og/twitter/generator meta")
    # emoji, speculation rules, wordfence, misc inline wp bits
    s = drop(r"<style id='wp-emoji-styles-inline-css'.*?</style>\s*", s, "wp-emoji inline style")
    s = drop(r"<script id=\"wp-emoji-settings\".*?</script>\s*", s, "wp-emoji settings script")
    s = drop(r"<script type=\"module\">(?:(?!</script>).)*?wp-emoji-loader(?:(?!</script>).)*?</script>\s*", s, "wp-emoji loader script")
    s = drop(r"<script type=\"speculationrules\">.*?</script>\s*", s, "speculationrules script")
    s = drop(r"<script type=\"text/javascript\">\s*\(function\(url\)\{(?:(?!</script>).)*?wordfence_lh(?:(?!</script>).)*?</script>\s*", s, "wordfence beacon script")
    s = drop(r"<style type=\"text/css\">\.recentcomments a\{[^<]*</style>\s*", s, "recentcomments style")
    # widgets
    def aside(m):
        t = m.group(0)
        if re.search(r"widget_(search|recent_comments|meta)\b", t[:200]) or re.search(r"coinbase|dwolla", t, re.I):
            bump("sidebar widget: " + re.search(r'id="([^"]*)"', t).group(1))
            return ""
        return t
    s = re.sub(r"<aside\b.*?</aside>\s*", aside, s, flags=re.S | re.I)
    # any other search form (e.g. 404 page)
    s = drop(r"<form[^>]*role=\"search\".*?</form>\s*", s, "search form")
    # comments: keep existing comment text, drop avatar/gravatar, reply, closed notice
    s = drop(r"<img[^>]*gravatar\.com[^>]*>", s, "gravatar avatar img")
    s = drop(r"<div class=\"reply\">\s*</div><!-- \.reply -->\s*", s, "empty reply div")
    s = drop(r"<p class=\"nocomments\">.*?</p>\s*", s, "'Comments are closed' notice")
    s = drop(r"<div id=\"respond\".*?</div><!-- #respond -->\s*", s, "comment form")
    s = drop(r"<a[^>]*class=\"comment-reply-link\"[^>]*>.*?</a>", s, "reply links")
    s = drop(r"<span class=\"comments-link\">.*?</span>", s, "comments-link")
    # empty comments-area container
    s = drop(r"<div id=\"comments\" class=\"comments-area\">\s*</div><!-- #comments \.comments-area -->\s*", s, "empty comments-area")
    return s

def process_html(raw_path, out_rel, page_dir):
    with open(raw_path, encoding="utf-8", errors="surrogateescape") as f:
        s = f.read()
    s = clean_html(s)
    ctx = out_rel
    s = ATTR.sub(lambda m: fix_attr(m, page_dir, ctx), s)
    # unwrap anchors that pointed at pages which 404 on the original site
    s = re.sub(r"<a\b[^>]*\0DEAD[^>]*>(.*?)</a>", r"\1", s, flags=re.S)
    assert "\0DEAD" not in s, "dead link outside <a>"
    # inline CSS: <style> blocks and style="" attributes
    s = re.sub(r"(<style\b[^>]*>)(.*?)(</style>)", lambda m: m.group(1) + fix_css(m.group(2), page_dir, ctx, False) + m.group(3), s, flags=re.S | re.I)
    s = re.sub(r"""(\sstyle\s*=\s*")([^"]*)(")""", lambda m: m.group(1) + (esc(fix_css(html.unescape(m.group(2)), page_dir, ctx, False)) if "url(" in m.group(2) else m.group(2)) + m.group(3), s, flags=re.I)
    s = re.sub(r"(<!DOCTYPE[^>]*>)", r"\1\n<!-- Static archive of the original WordPress site, captured on %s. Dynamic features (search, comments, login, donate buttons) were removed. -->" % DATE, s, count=1, flags=re.I)
    if out_rel == "404.html":
        # GitHub Pages serves 404.html at whatever URL was requested, so relative
        # links need a base. Compute it at runtime: the site root on a custom
        # domain, or /<repo>/ on a *.github.io project URL.
        s = s.replace("<head>", "<head>\n" + BASE_404, 1)
    return s

BASE_404 = (
    "<script>(function(){var p='/';"
    "if(/\\.github\\.io$/.test(location.hostname)){var s=location.pathname.split('/')[1];if(s)p='/'+s+'/';}"
    "var b=document.createElement('base');b.href=p;document.head.appendChild(b);})();</script>"
)

# ---------------------------------------------------------------- write
if os.path.exists(OUT):
    for n in os.listdir(OUT):
        if n in ("CNAME", ".nojekyll"):
            continue
        p = os.path.join(OUT, n)
        shutil.rmtree(p) if os.path.isdir(p) else os.remove(p)
os.makedirs(OUT, exist_ok=True)

for d, out_rel in pages.items():
    page_dir = "" if out_rel == "404.html" else d
    txt = process_html(files[(d + "/" if d else "") + "index.html"] if False else files[("%s/index.html" % d) if d else "index.html"], out_rel, page_dir)
    dest = os.path.join(OUT, out_rel)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest, "w", encoding="utf-8", errors="surrogateescape") as f:
        f.write(txt)

for a in assets:
    dest = os.path.join(OUT, a)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    if a.lower().endswith(".css"):
        with open(files[a], encoding="utf-8", errors="surrogateescape") as f:
            t = f.read()
        t = fix_css(t, posixpath.dirname(a), a)
        t = re.sub(r"""(@import\s+)(["'])(.*?)\2""", lambda m: m.group(1) + m.group(2) + (rewrite_url(m.group(3), posixpath.dirname(a), a) or m.group(3)) + m.group(2), t)
        with open(dest, "w", encoding="utf-8", errors="surrogateescape") as f:
            f.write(t)
    else:
        shutil.copyfile(files[a], dest)

open(os.path.join(OUT, ".nojekyll"), "a").close()
cname = os.path.join(OUT, "CNAME")
if not os.path.exists(cname):
    open(cname, "w").write("nextecon.org\n")

print("pages:", len(pages), "assets:", len(assets))
print("removed:"); [print("  %5d  %s" % (v, k)) for k, v in sorted(log["removed"].items())]
print("dead (404 on original) pages dropped:", log["dead"])
print("collisions:", log["collisions"])
print("relative-external fixed:", sorted(set(log["fixed_relative_external"])))
print("broken internal refs: %d" % len(log["broken"]))
for b in sorted(set(log["broken"])): print("  ", b)
