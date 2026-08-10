#!/usr/bin/env python3
"""Generate site/index.html from MANUAL.md.

MANUAL.md is the only hand-edited source. This produces the published document:
the design chrome comes from site/template.html, the content and every count
come from the manual. Running it twice on unchanged input yields identical
bytes, so CI can regenerate and diff to prove nothing drifted.
"""
from __future__ import annotations

import base64
import hashlib
import json
import re
import sys
from pathlib import Path
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.manual import REPO, load, slug  # noqa: E402
from lib.render import render  # noqa: E402

TEMPLATE = REPO / "site" / "template.html"
OUTPUT = REPO / "site" / "index.html"
THEME = REPO / "assets" / "mermaid-theme.json"
SITE_URL = "https://mlvpatel.github.io/open-weight-agent-stack/"
REPOSITORY_FILE_URL = "https://github.com/mlvpatel/open-weight-agent-stack/blob/main/"


def publish_repository_markdown_links(markdown: str) -> str:
    """Point source-document links at GitHub when rendering for Pages.

    GitHub Pages publishes only ``site/``. A relative Markdown link such as
    ``docs/MODELS.md`` is valid in the repository but becomes a 404 from the
    generated page. Keep the manual as the source of truth and make every
    existing, repository-local Markdown target a stable ``blob/main`` URL.
    Fenced code is deliberately left untouched so examples render verbatim.
    """

    def link(match: re.Match[str]) -> str:
        target = match.group("target")
        path, marker, fragment = target.partition("#")
        if not path.lower().endswith(".md"):
            return match.group(0)

        candidate = (REPO / path).resolve()
        try:
            relative = candidate.relative_to(REPO)
        except ValueError:
            return match.group(0)
        if not candidate.is_file():
            return match.group(0)

        url = REPOSITORY_FILE_URL + quote(relative.as_posix(), safe="/")
        if marker:
            url += "#" + quote(fragment, safe="-._~")
        return f"]({url})"

    parts = re.split(r"(```.*?```)", markdown, flags=re.S)
    for index in range(0, len(parts), 2):
        parts[index] = re.sub(r"(?<!!)\]\((?P<target>[^()\s]+)\)", link, parts[index])
    return "".join(parts)


def build() -> int:
    manual = load()
    theme = json.loads(THEME.read_text())
    init = "%%{init: " + json.dumps(theme, separators=(",", ":")) + "}%%\n"

    # The hero carries the title; drop the manual's H1 so it is not stated twice.
    md = re.sub(r"\A# [^\n]*\n", "", manual.text, count=1)
    md = publish_repository_markdown_links(md)
    body, figures = render(md, init)

    # Contents, derived from the manual's own numbered sections.
    toc = "".join(
        f'<li><a href="#{slug(h)}"><span class="n">{h.split(".")[0].zfill(2)}</span>'
        f' {h.split(". ", 1)[1] if ". " in h else h}</a></li>'
        for h in manual.sections
    )

    # Every number below is measured, never typed.
    facts = {
        "SECTIONS": str(manual.section_count),
        "DIAGRAMS": str(manual.diagram_count),
        "FIGURES": str(figures),
        "LINKS": str(manual.link_count),
        "UNIQUE_LINKS": str(manual.unique_links),
        "SITE_URL": SITE_URL,
        "TOC": toc,
        "BODY": body,
    }

    out = TEMPLATE.read_text()
    for key, value in facts.items():
        out = out.replace("{{" + key + "}}", value)

    # The CSP hash must cover the exact bytes of the inline script as emitted,
    # so it is computed here rather than written into the template by hand.
    # GitHub Pages cannot send response headers, so this is a meta CSP:
    # frame-ancestors, report-uri and sandbox are ignored in that form per the
    # spec, and everything else applies. style-src permits inline because
    # Mermaid injects styles while rendering.
    inline = re.search(r"<script>(.*?)</script>", out, re.S)
    if not inline:
        print("error: no inline script found; the CSP hash would be wrong", file=sys.stderr)
        return 1
    digest = base64.b64encode(hashlib.sha256(inline.group(1).encode()).digest()).decode()
    csp = (
        "default-src 'none'; "
        f"script-src 'self' 'sha256-{digest}'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; "
        "font-src 'self'; "
        "connect-src 'none'; "
        "base-uri 'none'; "
        "form-action 'none'"
    )
    out = out.replace("{{CSP}}", csp)

    leftover = re.findall(r"\{\{[A-Z_]+\}\}", out)
    if leftover:
        print(f"error: unfilled placeholders {sorted(set(leftover))}", file=sys.stderr)
        return 1

    OUTPUT.write_text(out)
    print(f"generated {OUTPUT.relative_to(REPO)}: "
          f"{manual.section_count} sections, {figures} figures, {manual.link_count} links")
    return 0


if __name__ == "__main__":
    raise SystemExit(build())
