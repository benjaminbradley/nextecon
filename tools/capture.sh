#!/usr/bin/env bash
# Capture http://nextecon.org into a raw wget mirror. Usage: capture.sh RAW_DIR (must be new/empty)
set -u
RAW="${1:?usage: capture.sh RAW_DIR}"
mkdir -p "$RAW"
SEEDS="$RAW/seeds.txt"
BASE=http://nextecon.org
: > "$SEEDS"
echo "$BASE/" >> "$SEEDS"
for sm in $(curl -s "$BASE/wp-sitemap.xml" | grep -o '<loc>[^<]*</loc>' | sed 's/<[^>]*>//g'); do
  curl -s "$sm" | grep -o '<loc>[^<]*</loc>' | sed 's/<[^>]*>//g' >> "$SEEDS"
done
# extra: 404 page for theme styling
echo "$BASE/this-page-does-not-exist-404/" >> "$SEEDS"
sort -u "$SEEDS" -o "$SEEDS"
wget --recursive --level=inf --page-requisites --no-parent=off \
  --span-hosts=off --domains=nextecon.org -e robots=off --wait=0.5 \
  --restrict-file-names=unix --content-on-error \
  --reject-regex '(/wp-admin|wp-login\.php|xmlrpc\.php|/wp-json|/feed/?($|\?)|/comments/|replytocom=|[?&]p=|[?&]s=|/oembed|[?&]format=|/embed/?$|/wp-content/uploads/?(\?.*)?$)' \
  --directory-prefix="$RAW" --input-file="$SEEDS" \
  -o "$RAW/wget.log"
