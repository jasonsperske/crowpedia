#!/usr/bin/env python3
"""Check that every post's text survived the migration.

Usage: python3 -I tools/verify.py <legacy-mirror-dir> <hugo-public-dir>
"""
import html
import re
import sys
from pathlib import Path


def words(fragment):
    text = html.unescape(re.sub(r"<[^>]+>", " ", fragment))
    return re.findall(r"\w+", text.lower())


def legacy_body(page):
    return re.search(r"role='main'>\s*<h1>.*?</h1>(.*?)</div>\s*<div class='col-md-3'>", page, re.S).group(1)


def new_body(page):
    if "<article class=post>" in page or '<article class="post">' in page:
        body = re.search(r"<article class=\"?post\"?>.*?</header>(.*?)</article>", page, re.S).group(1)
        return body
    # Undated page: message bodies, minus the headings, dates and estimates.
    parts = re.findall(r"<article class=\"?message\"?[^>]*>(.*?)</article>", page, re.S)
    out = []
    for i, part in enumerate(parts, 1):
        part = re.sub(r"<details.*?</details>|<p class=\"?meta\"?>.*?</p>|<h2>.*?</h2>", "", part, flags=re.S)
        out.append(f"<h3>Message:{i}</h3>{part}")
    return "".join(out)


legacy, public = Path(sys.argv[1]), Path(sys.argv[2])
failures = 0
for old in sorted((legacy / "posts").glob("*/*-*.html")) + [legacy / "posts/AOL/Unknown.html"]:
    rel = old.relative_to(legacy)
    new = public / rel
    a, b = words(legacy_body(old.read_text())), words(new_body(new.read_text()))
    if a != b:
        failures += 1
        print(f"MISMATCH {rel}: {len(a)} vs {len(b)} words")
print(f"{failures} mismatches")
sys.exit(1 if failures else 0)
