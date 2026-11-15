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
import html as html_lib
import json
import re
import sys
from pathlib import Path
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.manual import REPO, load, slug, split_fences  # noqa: E402
from lib.render import render  # noqa: E402

SITE_URL = "https://mlvpatel.github.io/open-weight-agent-stack/"
REPOSITORY_FILE_URL = "https://github.com/mlvpatel/open-weight-agent-stack/blob/main/"
PUBLISHED_MARKDOWN_PAGES = {
    "MANUAL.md": "index.html",
    "docs/ARCHITECTURE.md": "architecture.html",
    "docs/MODELS.md": "models.html",
}
ARCHITECTURE_FIGURES = ("System context", "Containers", "Components")
# The template owns the one inline script. Rendered markdown cannot add another,
# because every path through lib/render.py escapes "<".
_INLINE_SCRIPT = re.compile(r"<script\b(?![^>]*\bsrc=)[^>]*>(.*?)</script>", re.S | re.I)


def _rewrite_prose_links(prose: str, repo: Path, source: Path | None = None) -> str:
    """Rewrite repository markdown links, leaving inline code spans untouched."""
    spans: list[str] = []
    base = source.parent if source is not None else repo

    def stash(match: re.Match[str]) -> str:
        spans.append(match.group(0))
        return f"\x00{len(spans) - 1}\x00"

    held = re.sub(r"`[^`]+`", stash, prose)

    def link(match: re.Match[str]) -> str:
        target = match.group("target")
        path, marker, fragment = target.partition("#")
        if path.startswith(("http://", "https://", "mailto:", "#")):
            return match.group(0)

        candidate = (base / path).resolve()
        try:
            relative = candidate.relative_to(repo.resolve())
        except ValueError:
            return match.group(0)
        if not candidate.is_file():
            return match.group(0)

        published = PUBLISHED_MARKDOWN_PAGES.get(relative.as_posix())
        if published:
            url = published
        else:
            url = REPOSITORY_FILE_URL + quote(relative.as_posix(), safe="/")
        if marker:
            url += "#" + quote(fragment, safe="-._~")
        return f"]({url})"

    rewritten = re.sub(r"(?<!!)\]\((?P<target>[^()\s]+)\)", link, held)
    return re.sub(r"\x00(\d+)\x00", lambda match: spans[int(match.group(1))], rewritten)


def publish_repository_markdown_links(
    markdown: str, repo: Path = REPO, source: Path | None = None
) -> str:
    """Point source-document links at published pages or GitHub.

    GitHub Pages publishes only ``site/``. Companion docs that the nav renders
    become same-origin HTML; every other repository file becomes a stable
    ``blob/main`` URL. Fenced code and inline code spans are left untouched so
    examples render verbatim. Links are resolved relative to ``source`` when
    given, which is how ``docs/ARCHITECTURE.md`` can say ``../MANUAL.md``.
    """
    out: list[str] = []
    for fence, chunk in split_fences(markdown):
        out.append(chunk if fence else _rewrite_prose_links(chunk, repo, source))
    return "".join(out)


def _csp_for(document: str) -> str | None:
    """CSP pinning the document's single inline script by hash, or None if there isn't exactly one."""
    scripts = _INLINE_SCRIPT.findall(document)
    if len(scripts) != 1:
        return None
    digest = base64.b64encode(hashlib.sha256(scripts[0].encode()).digest()).decode()
    return (
        "default-src 'none'; "
        f"script-src 'self' 'sha256-{digest}'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; "
        "font-src 'self'; "
        "connect-src 'none'; "
        "base-uri 'none'; "
        "form-action 'none'"
    )


def _fill_template(template: str, facts: dict[str, str]) -> str | None:
    """Substitute chrome first, hash the script, then drop BODY in last."""
    out = template
    for key, value in facts.items():
        if key not in {"BODY", "CSP"}:
            out = out.replace("{{" + key + "}}", value)
    csp = _csp_for(out)
    if csp is None:
        return None
    out = out.replace("{{CSP}}", csp).replace("{{BODY}}", facts["BODY"])
    leftover = re.findall(r"\{\{[A-Z_]+\}\}", out)
    if leftover:
        print(f"error: unfilled placeholders {sorted(set(leftover))}", file=sys.stderr)
        return None
    return out


def _nav(current: str) -> dict[str, str]:
    facts: dict[str, str] = {}
    for key, href in (("manual", "index.html"), ("architecture", "architecture.html"), ("models", "models.html")):
        facts[f"NAV_{key.upper()}_HREF"] = "#main" if key == current == "manual" else href
        facts[f"NAV_{key.upper()}_CUR"] = ' aria-current="page"' if key == current else ""
    return facts


def build(repo: Path = REPO) -> int:
    """Render the manual and the two companion docs without mutating another checkout."""
    template = (repo / "site" / "template.html").read_text(encoding="utf-8")
    theme = json.loads((repo / "assets" / "mermaid-theme.json").read_text(encoding="utf-8"))
    init = "%%{init: " + json.dumps(theme, separators=(",", ":")) + "}%%\n"
    manual = load(repo / "MANUAL.md")

    md = re.sub(r"\A# [^\n]*\n", "", manual.text, count=1)
    md = publish_repository_markdown_links(md, repo, source=repo / "MANUAL.md")
    body, figures = render(md, init)
    toc = "".join(
        f'<li><a href="#{slug(h)}"><span class="n">{h.split(".")[0].zfill(2)}</span>'
        f' {h.split(". ", 1)[1] if ". " in h else h}</a></li>'
        for h in manual.sections
    )
    shared = {
        "SECTIONS": str(manual.section_count),
        "DIAGRAMS": str(manual.diagram_count),
        "SITE_URL": SITE_URL,
    }

    manual_html = _fill_template(template, {
        **shared,
        **_nav("manual"),
        "TOC": toc,
        "BODY": body,
        "PAGE_TITLE": "The Open-Weight Agent Stack, Build Manual",
        "CANONICAL": SITE_URL,
    })
    if manual_html is None:
        print("error: expected exactly one complete inline script; the CSP hash would be wrong", file=sys.stderr)
        return 1
    (repo / "site" / "index.html").write_text(manual_html, encoding="utf-8")

    companions = (
        ("architecture", repo / "docs" / "ARCHITECTURE.md", ARCHITECTURE_FIGURES,
         "Architecture, in C4", SITE_URL + "architecture.html"),
        ("models", repo / "docs" / "MODELS.md", (),
         "Open-weight model families and their licences", SITE_URL + "models.html"),
    )
    for name, source, titles, page_title, canonical in companions:
        doc = load(source)
        stripped = re.sub(r"\A# [^\n]*\n", "", doc.text, count=1)
        text = publish_repository_markdown_links(stripped, repo, source=source)
        page_body, _page_figs = render(text, init, figure_titles=titles)
        page_toc = "".join(
            f'<li><a href="#{slug(heading)}">{html_lib.escape(heading)}</a></li>'
            for level, heading in doc.headings if level == 2
        )
        filled = _fill_template(template, {
            **shared,
            **_nav(name),
            "TOC": page_toc,
            "BODY": page_body,
            "PAGE_TITLE": page_title,
            "CANONICAL": canonical,
        })
        if filled is None:
            print(f"error: failed to hash inline script for {name}", file=sys.stderr)
            return 1
        (repo / "site" / f"{name}.html").write_text(filled, encoding="utf-8")

    print(f"generated site/index.html: "
          f"{manual.section_count} sections, {figures} figures, {manual.link_count} links")
    print("generated site/architecture.html and site/models.html")
    return 0


if __name__ == "__main__":
    raise SystemExit(build())
