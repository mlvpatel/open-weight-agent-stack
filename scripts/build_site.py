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
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.manual import REPO, load, slug  # noqa: E402
from lib.render import render  # noqa: E402

SITE_URL = "https://mlvpatel.github.io/open-weight-agent-stack/"
REPOSITORY_FILE_URL = "https://github.com/mlvpatel/open-weight-agent-stack/blob/main/"
PUBLISHED_MARKDOWN_PAGES = {
    "MANUAL.md": "index.html",
    "docs/ARCHITECTURE.md": "architecture.html",
    "docs/MODELS.md": "models.html",
}
ARCHITECTURE_FIGURES = ("System context", "Containers", "Components")
_FENCE_OPEN = re.compile(r"^(?P<mark>`{3,}|~{3,})", re.M)


class _InlineScriptCollector(HTMLParser):
    """Collect exact inline-script bodies; ``HTMLParser`` normalizes tag case."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self.scripts: list[str] = []
        self._chunks: list[str] | None = None

    @property
    def incomplete(self) -> bool:
        return self._chunks is not None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "script" or any(name.lower() == "src" for name, _ in attrs):
            return
        if self._chunks is not None:
            return
        self._chunks = []

    def handle_data(self, data: str) -> None:
        if self._chunks is not None:
            self._chunks.append(data)

    def handle_entityref(self, name: str) -> None:
        if self._chunks is not None:
            self._chunks.append(f"&{name};")

    def handle_charref(self, name: str) -> None:
        if self._chunks is not None:
            self._chunks.append(f"&#{name};")

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "script" and self._chunks is not None:
            self.scripts.append("".join(self._chunks))
            self._chunks = None


def extract_single_inline_script(document: str) -> str | None:
    """Return the sole complete inline script, or ``None`` if ambiguous."""
    parser = _InlineScriptCollector()
    parser.feed(document)
    parser.close()
    if parser.incomplete or len(parser.scripts) != 1:
        return None
    return parser.scripts[0]


def _split_fences(markdown: str) -> list[tuple[bool, str]]:
    """Split markdown into (is_fence, text) covering 3+ backtick or tilde fences."""
    parts: list[tuple[bool, str]] = []
    cursor = 0
    for match in _FENCE_OPEN.finditer(markdown):
        if match.start() < cursor:
            continue
        mark = match.group("mark")
        closer = re.compile(r"^" + re.escape(mark) + r"[ \t]*$", re.M)
        rest = markdown[match.end():]
        close = closer.search(rest)
        if close is None:
            break
        end = match.end() + close.end()
        if match.start() > cursor:
            parts.append((False, markdown[cursor:match.start()]))
        parts.append((True, markdown[match.start():end]))
        cursor = end
    if cursor < len(markdown):
        parts.append((False, markdown[cursor:]))
    return parts or [(False, markdown)]


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
    for is_fence, chunk in _split_fences(markdown):
        out.append(chunk if is_fence else _rewrite_prose_links(chunk, repo, source))
    return "".join(out)


def _csp_for(document: str) -> str | None:
    inline = extract_single_inline_script(document)
    if inline is None:
        return None
    digest = base64.b64encode(hashlib.sha256(inline.encode()).digest()).decode()
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
    body = facts["BODY"]
    for key, value in facts.items():
        if key in {"BODY", "CSP"}:
            continue
        out = out.replace("{{" + key + "}}", value)
    csp = _csp_for(out.replace("{{BODY}}", "").replace("{{CSP}}", "PENDING"))
    if csp is None:
        return None
    # Hash against the document the browser will see, including BODY.
    trial = out.replace("{{CSP}}", csp).replace("{{BODY}}", body)
    final_csp = _csp_for(trial)
    if final_csp is None:
        return None
    out = out.replace("{{CSP}}", final_csp).replace("{{BODY}}", body)
    leftover = re.findall(r"\{\{[A-Z_]+\}\}", out)
    if leftover:
        print(f"error: unfilled placeholders {sorted(set(leftover))}", file=sys.stderr)
        return None
    return out


def _nav(current: str) -> dict[str, str]:
    pages = {
        "manual": ("index.html", "Manual"),
        "architecture": ("architecture.html", "Architecture"),
        "models": ("models.html", "Models"),
    }
    facts: dict[str, str] = {}
    for key, (href, _label) in pages.items():
        attr = ' aria-current="page"' if key == current else ""
        facts[f"NAV_{key.upper()}_HREF"] = "#" + "main" if key == "manual" and current == "manual" else href
        facts[f"NAV_{key.upper()}_CUR"] = attr
    if current == "manual":
        facts["NAV_MANUAL_HREF"] = "#main"
    return facts


def _write_page(path: Path, html: str) -> None:
    path.write_text(html, encoding="utf-8")


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
        "FIGURES": str(figures),
        "LINKS": str(manual.link_count),
        "UNIQUE_LINKS": str(manual.unique_links),
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
    _write_page(repo / "site" / "index.html", manual_html)

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
        _write_page(repo / "site" / f"{name}.html", filled)

    print(f"generated site/index.html: "
          f"{manual.section_count} sections, {figures} figures, {manual.link_count} links")
    print("generated site/architecture.html and site/models.html")
    return 0


if __name__ == "__main__":
    raise SystemExit(build())
