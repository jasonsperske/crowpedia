#!/usr/bin/env python3
"""Build the repository's git history so it mirrors the archive's timeline.

Every post is committed on the day it was written (or its estimated date, for
the undated AOL messages). The site's own editorial text is committed on the
date the original crowpedia.com went up, and the Hugo site itself is committed
as of now.

Usage: python3 -I tools/replay_history.py [--dry-run] <repo-dir>

The directory must not contain a .git yet. To redo the history (say, after
changing a date estimate) delete .git and run this again -- but only before
the repository has been pushed anywhere, since it rewrites every commit.
"""
import os
import subprocess
import sys
import tomllib
from datetime import date, datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo

# Posts are stamped at noon Pacific, where the band was based.
PACIFIC = ZoneInfo("America/Los_Angeles")
# Last-Modified of the legacy site on S3: Sat, 12 Apr 2014 23:57:08 GMT.
ORIGINAL_SITE = datetime(2014, 4, 12, 23, 57, 8, tzinfo=ZoneInfo("UTC")).astimezone(PACIFIC)
TRAILER = "\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>\n"
SOURCES = {"aol": "AOL message board", "newsgroup": "Emerald.net newsgroup"}


def front_matter(path):
    text = path.read_text()
    return tomllib.loads(text.split("+++\n")[1])


def post_commits(repo):
    commits = []
    for path in (repo / "content" / "posts").rglob("*.md"):
        if path.name == "_index.md":
            continue
        meta = front_matter(path)
        when = meta["date"]
        if not isinstance(when, date):
            sys.exit(f"{path}: date must be a TOML date, got {when!r}")
        stamp = datetime.combine(when, time(12), PACIFIC)
        author = meta.get("author", "Adam Duritz")
        if "date_estimate" in meta:
            est = meta["date_estimate"]
            message = (f"Archive undated AOL message {meta['archive_position']} "
                       f"(est. {when:%B %Y})\n\n"
                       f"Estimated between {est['earliest']} and {est['latest']}, "
                       f"{est['confidence']} confidence:\n"
                       + "".join(f"- {e}\n" for e in est["evidence"]))
        else:
            message = f"Archive {author}'s {SOURCES[meta['source']]} post of {when:%B %-d, %Y}\n"
        commits.append((stamp, [path], message))
    return sorted(commits, key=lambda c: (c[0], str(c[1][0])))


def git(repo, *args, when=None, dry_run=False):
    env = dict(os.environ)
    if when:
        env["GIT_AUTHOR_DATE"] = env["GIT_COMMITTER_DATE"] = when.isoformat()
    if dry_run:
        print("  git", *args[:2], f"[{when:%Y-%m-%d}]" if when else "")
        return
    subprocess.run(["git", "-C", str(repo), *args], check=True, env=env,
                   stdout=subprocess.DEVNULL)


def main():
    args = sys.argv[1:]
    dry_run = "--dry-run" in args
    repo = Path([a for a in args if a != "--dry-run"][0]).resolve()
    if (repo / ".git").exists() and not dry_run:
        sys.exit(f"{repo} already has a .git; delete it first to rebuild the history")

    git(repo, "init", "--initial-branch=main", dry_run=dry_run)
    commits = post_commits(repo)
    for when, paths, message in commits:
        git(repo, "add", "--", *map(str, paths), dry_run=dry_run)
        git(repo, "commit", "--quiet", "-m", message + TRAILER, when=when, dry_run=dry_run)

    # The editorial text (home page, section introductions and notes) was
    # written for the original 2014 site.
    indexes = sorted(str(p) for p in (repo / "content").rglob("_index.md"))
    git(repo, "add", "--", *indexes, dry_run=dry_run)
    git(repo, "commit", "--quiet", "-m",
        "Publish the original Crowpedia site\n\n"
        "Home page and section introductions, as first published on crowpedia.com.\n" + TRAILER,
        when=ORIGINAL_SITE, dry_run=dry_run)

    # Everything else is the modern Hugo site.
    git(repo, "add", "--all", dry_run=dry_run)
    git(repo, "commit", "--quiet", "-m",
        "Rebuild Crowpedia with Hugo for GitHub Pages\n\n"
        "Replace the 2014 Bootstrap/jQuery site with Hugo templates, keeping\n"
        "every legacy /posts/... URL, and deploy with GitHub Actions.\n" + TRAILER,
        dry_run=dry_run)
    print(f"{len(commits)} post commits + 2 site commits")


if __name__ == "__main__":
    main()
