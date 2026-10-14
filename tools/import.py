#!/usr/bin/env python3
"""One-time importer: convert a wget mirror of the legacy crowpedia.com into
Hugo content (Markdown bodies with TOML front matter).

Usage: python3 -I tools/import.py <mirror-dir> <content-dir>

Only the standard library is used so the script runs anywhere.
"""
import html
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

MONTHS = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()


class Markdownifier(HTMLParser):
    """Tiny HTML -> Markdown converter covering the tags the legacy site used:
    p, hr, h3, b/strong, i/em, a, pre/code, br, ul/li."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out = []
        self.in_pre = False
        self.href = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in ("p", "ul", "pre"):
            self.out.append("\n\n")
        if tag == "pre":
            self.in_pre = True
            self.out.append("```\n")
        elif tag == "hr":
            self.out.append("\n\n---\n\n")
        elif tag in ("h2", "h3"):
            self.out.append("\n\n" + "#" * int(tag[1]) + " ")
        elif tag in ("b", "strong"):
            self.out.append("**")
        elif tag in ("i", "em"):
            self.out.append("*")
        elif tag == "br":
            self.out.append("  \n")
        elif tag == "li":
            self.out.append("\n- ")
        elif tag == "code" and not self.in_pre:
            self.out.append("`")
        elif tag == "a":
            self.href = attrs.get("href")
            self.out.append("[")

    def handle_endtag(self, tag):
        if tag in ("p", "h2", "h3", "ul"):
            self.out.append("\n\n")
        elif tag == "pre":
            self.in_pre = False
            self.out.append("\n```\n\n")
        elif tag in ("b", "strong"):
            self.out.append("**")
        elif tag in ("i", "em"):
            self.out.append("*")
        elif tag == "code" and not self.in_pre:
            self.out.append("`")
        elif tag == "a":
            self.out.append(f"]({self.href})")

    def handle_data(self, data):
        if self.in_pre:
            self.out.append(data)
            return
        # Escape characters Markdown would otherwise interpret inline.
        data = re.sub(r"([\\`*_\[\]<])", r"\\\1", data)
        self.out.append(data)

    def markdown(self):
        text = "".join(self.out)
        lines = []
        for line in text.split("\n"):
            # Neutralise things that would become block syntax at line start.
            line = re.sub(r"^(\s*)([#>+=-])", r"\1\\\2", line) if not re.match(r"(#{2,3} |---|- |```)", line) else line
            line = re.sub(r"^(\s*\d+)([.)])", r"\1\\\2", line)
            lines.append(line.rstrip() if not line.endswith("  ") else line)
        text = "\n".join(lines)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip() + "\n"


def to_markdown(fragment):
    parser = Markdownifier()
    parser.feed(fragment)
    parser.close()
    return parser.markdown()


def main_block(page):
    """The post body: everything inside role='main' after the <h1>."""
    m = re.search(r"role='main'>\s*<h1>(.*?)</h1>(.*?)</div>\s*<div class='col-md-3'>", page, re.S)
    return html.unescape(m.group(1)).strip(), m.group(2)


def note_block(page):
    m = re.search(r'<div class="panel-body">(.*?)</div>', page, re.S)
    if not m:
        return None
    # Panel bodies are bare text, so wrap blank-line separated chunks in <p>.
    body = m.group(1).strip()
    body = "".join(f"<p>{chunk}</p>" for chunk in re.split(r"\n\s*\n", body))
    return to_markdown(body)


def toml_str(value):
    if "\n" in value:
        return '"""\n' + value.replace("\\", "\\\\").replace('"""', '\\"""') + '"""'
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def write(path, front, body=""):
    lines = ["+++"]
    tables = {k: v for k, v in front.items() if isinstance(v, dict)}
    for key, value in front.items():
        if key in tables:
            continue
        if key == "date":
            pass  # TOML local date, not a string
        elif isinstance(value, str):
            value = toml_str(value)
        elif isinstance(value, list):
            value = "[" + ", ".join(toml_str(v) for v in value) + "]"
        elif isinstance(value, bool):
            value = str(value).lower()
        lines.append(f"{key} = {value}")
    for name, table in tables.items():
        lines.append(f"\n[{name}]")
        for key, value in table.items():
            lines.append(f"{key} = {toml_str(value) if isinstance(value, str) else value}")
    lines.append("+++")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n" + (body and "\n" + body))
    print("wrote", path)


SOURCES = {"AOL": "aol", "Newsgroup": "newsgroup"}


def import_dated(mirror, content):
    for page_path in sorted((mirror / "posts").glob("*/????-??-??.html")):
        page = page_path.read_text()
        title, body = main_block(page)
        source = SOURCES[page_path.parent.name]
        date = page_path.stem
        front = {
            "title": title,
            "date": date,
            "source": source,
            "url": f"/posts/{page_path.parent.name}/{page_path.name}",
        }
        if "MATT POST" in body:
            front["author"] = "Matt Malley"
        note = note_block(page)
        if note:
            front["note"] = note
        write(content / "posts" / source / date[:4] / f"{date}.md", front, to_markdown(body))


def import_year_indexes(mirror, content):
    for page_path in sorted((mirror / "posts").glob("*/????.html")):
        page = page_path.read_text()
        title, _ = main_block(page)
        source = SOURCES[page_path.parent.name]
        front = {
            "title": title,
            "url": f"/posts/{page_path.parent.name}/{page_path.name}",
        }
        note = note_block(page)
        write(content / "posts" / source / page_path.stem / "_index.md", front, note or "")


def import_undated(mirror, content):
    page = (mirror / "posts" / "AOL" / "Unknown.html").read_text()
    title, body = main_block(page)
    front = {"title": title, "url": "/posts/AOL/Unknown.html"}
    write(content / "posts" / "aol" / "undated" / "_index.md", front, note_block(page))
    chunks = re.split(r"<h3>Message:(\d+)</h3>", body)[1:]
    for number, chunk in zip(chunks[::2], chunks[1::2]):
        n = int(number)
        front = {
            "title": f"Message {n}",
            # Zak's archive listed the newest message first; `weight` keeps
            # that original order, `date` is filled in by the dating pass.
            "weight": n,
            "source": "aol",
            "archive_position": n,
        }
        write(content / "posts" / "aol" / "undated" / f"msg-{n:02d}.md", front, to_markdown(chunk))


def import_home(mirror, content):
    page = (mirror / "index.html").read_text()
    m = re.search(r'<div class="jumbotron">\s*<h1>(.*?)</h1>\s*<p>(.*?)</p>\s*</div>(.*?)\s*</div>\s*<div id="footer">', page, re.S)
    front = {"title": html.unescape(m.group(1)), "description": html.unescape(m.group(2))}
    write(content / "_index.md", front, to_markdown(m.group(3)))


def main():
    mirror, content = Path(sys.argv[1]), Path(sys.argv[2])
    import_home(mirror, content)
    import_year_indexes(mirror, content)
    import_dated(mirror, content)
    import_undated(mirror, content)


if __name__ == "__main__":
    main()
