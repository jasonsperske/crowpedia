# Crowpedia

An archive of Adam Duritz's message board posts (AOL and the Emerald.net
newsgroup, 1995–2000), published at <https://crowpedia.com/> with Hugo and
GitHub Pages.

## Layout

| Path | What it holds |
| --- | --- |
| `content/posts/<source>/<year>/<date>.md` | One post: Markdown body, TOML front matter (`date`, `source`, `url`, optional `author` and `note`) |
| `content/posts/<source>/<year>/_index.md` | A year page; its body is the "Of note" box |
| `content/posts/aol/undated/msg-NN.md` | The 25 pre-website AOL messages, with a `[date_estimate]` table explaining each estimated date |
| `layouts/` | Hugo templates |
| `assets/css/site.css` | The only stylesheet |
| `tools/` | One-time migration and history scripts |

Every legacy URL (`/posts/AOL/1998-03-15.html` and so on) is kept via each
page's `url` and `uglyURLs = true`.

## Working on it

```sh
hugo server          # preview at http://localhost:1313
hugo --minify        # build into public/
```

Pushing to `main` deploys through `.github/workflows/pages.yml`.

## Dating the undated messages

Zak's original archive listed the AOL messages newest first, so archive
position gives their order. Messages with internal clues are anchored to known
events (Adam's birthday, Charlie Gillingham's birthday, the writing of "A Long
December" in January 1996, *The Crossing Guard*'s release, the planned August
1996 release); the rest are spaced evenly between anchors. Each message's
`[date_estimate]` records the range, confidence and evidence, and the site
shows it under "Why this date?".

## Git history

`tools/replay_history.py` builds the history so it follows the archive: each
post is committed on its own (or estimated) date, the editorial text on the
date the original site went up (12 April 2014), and the Hugo site as of the
migration. Changing a date means deleting `.git` and re-running it, which is
only safe before the repository has been pushed.

## Migration tools

- `tools/import.py <mirror> content` converted a `wget` mirror of the old site.
- `tools/verify.py <mirror> <public>` checks every post's words survived.
