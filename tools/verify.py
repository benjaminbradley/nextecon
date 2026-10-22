#!/usr/bin/env python3
"""Check every internal ref in DOCS_DIR resolves to a file. usage: python3 -I verify.py DOCS_DIR"""
import html, os, posixpath, re, sys
from urllib.parse import urlsplit, unquote
D = sys.argv[1]
ATTR = re.compile(r"""\s(href|src|srcset|action|poster)\s*=\s*(["'])(.*?)\2""", re.I | re.S)
CSSURL = re.compile(r"""url\(\s*(["']?)(.*?)\1\s*\)""", re.S)
bad, n, ext, rootrel = [], 0, 0, []
def check(src, u):
    global n, ext
    u = html.unescape(u).strip()
    if not u or u[0] == "#" or re.match(r"(mailto|tel|data|javascript):", u, re.I): return
    if re.match(r"(https?:)?//", u): 
        ext += 1
        if re.match(r"(https?:)?//(www\.)?nextecon\.org", u): bad.append((src, u, "absolute internal"))
        return
    if src == "404.html" and u == "/": return  # <base href="/">
    if u.startswith("/"): rootrel.append((src, u))
    n += 1
    p = unquote(urlsplit(u).path)
    base = "" if src == "404.html" else posixpath.dirname(src)
    t = posixpath.normpath(posixpath.join(base, p)) if p else src
    if t == ".": t = ""
    full = os.path.join(D, t)
    if os.path.isdir(full):
        if not (p.endswith("/") or p == ""): bad.append((src, u, "dir link without trailing slash")); return
        full = os.path.join(full, "index.html")
    if not os.path.isfile(full): bad.append((src, u, "missing"))
for root, _, names in os.walk(D):
    for fn in names:
        path = os.path.join(root, fn); rel = os.path.relpath(path, D)
        if fn.endswith((".html", ".css")):
            s = open(path, encoding="utf-8", errors="replace").read()
            if fn.endswith(".html"):
                for m in ATTR.finditer(s):
                    if m.group(1).lower() == "srcset":
                        for e in re.split(r",\s+", html.unescape(m.group(3)).strip()): check(rel, e.split()[0])
                    else: check(rel, m.group(3))
                for m in re.finditer(r"<style\b[^>]*>(.*?)</style>|\sstyle=\"([^\"]*)\"", s, re.S):
                    for c in CSSURL.finditer(m.group(1) or m.group(2) or ""): check(rel, c.group(2))
            else:
                for c in CSSURL.finditer(s): check(rel, c.group(2))
print("internal refs checked:", n, "| external refs left alone:", ext)
print("root-relative refs:", rootrel)
print("problems:", len(bad)); [print("  ", b) for b in bad]
sys.exit(1 if bad or rootrel else 0)
