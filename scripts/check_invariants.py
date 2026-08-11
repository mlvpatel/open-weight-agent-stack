#!/usr/bin/env python3
"""Fail on the drift classes this repository has actually suffered.

Every check reports how many items it inspected. A check whose input matches
nothing fails rather than passing silently, because a gate that inspects zero
items and reports success is worse than no gate: it produces false confidence.

Checks:
  anchors   every internal MANUAL.md#anchor reference resolves
  files     every relative markdown link points at a file that exists
  counts    every count stated in prose matches the measured value
  desc      the GitHub repository description agrees with the repository
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.manual import REPO, load, markdown_files  # noqa: E402

FAILURES: list[str] = []
SUMMARY: list[str] = []


def fail(msg: str) -> None:
    FAILURES.append(msg)


def require_nonzero(name: str, n: int, what: str) -> None:
    """A gate that inspected nothing has proven nothing."""
    if n == 0:
        fail(f"{name}: inspected 0 {what}. The gate matched nothing, so it is not enforcing anything.")


def check_anchors(m) -> None:
    checked = 0
    for f in markdown_files():
        text = f.read_text()
        for ref in re.finditer(r"\]\(([^)]*MANUAL\.md)#([a-z0-9-]+)\)", text):
            checked += 1
            anchor = ref.group(2)
            if anchor not in m.anchors:
                fail(f"anchors: {f.relative_to(REPO)} links to MANUAL.md#{anchor}, which no heading produces")
    require_nonzero("anchors", checked, "anchor references")
    SUMMARY.append(f"anchors: {checked} references checked against {len(m.anchors)} headings")


def check_relative_files() -> None:
    checked = 0
    for f in markdown_files():
        for ref in re.finditer(r"\]\(([^)#]+\.(?:md|png|json|svg))(?:#[^)]*)?\)", f.read_text()):
            target = ref.group(1)
            if target.startswith(("http://", "https://", "//")):
                continue
            checked += 1
            if not (f.parent / target).resolve().exists():
                fail(f"files: {f.relative_to(REPO)} links to {target}, which does not exist")
    require_nonzero("files", checked, "relative links")
    SUMMARY.append(f"files: {checked} relative links resolved")


class _GeneratedURLCollector(HTMLParser):
    """Collect the URLs that a browser resolves from generated markup."""

    def __init__(self) -> None:
        super().__init__()
        self.urls: list[tuple[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        for name, value in attrs:
            if name in {"href", "src"} and value:
                self.urls.append((f"{tag}[{name}]", value))


def check_generated_site_links() -> None:
    """Ensure every generated relative URL resolves inside ``site/``.

    This protects the deployed Pages document, whose URL base differs from the
    repository root. External URLs and fragments are intentionally outside the
    scope of this structural check and remain the link-check job's concern.
    """
    site = REPO / "site" / "index.html"
    if not site.exists():
        fail("generated-links: expected site/index.html")
        return

    site_root = site.parent.resolve()
    collector = _GeneratedURLCollector()
    collector.feed(site.read_text())
    checked = 0
    for source, url in collector.urls:
        parsed = urlsplit(url)
        if parsed.scheme or parsed.netloc or not parsed.path:
            continue
        if parsed.path.startswith("/"):
            fail(f"generated-links: {source} uses root-relative URL {url!r}; Pages is published below a repository path")
            continue
        checked += 1
        target = (site_root / unquote(parsed.path)).resolve()
        try:
            target.relative_to(site_root)
        except ValueError:
            fail(f"generated-links: {source} escapes site/ via {url!r}")
            continue
        if not target.is_file():
            fail(f"generated-links: {source} points to {url!r}, which site/ does not publish")
    require_nonzero("generated-links", checked, "site-relative URLs")
    SUMMARY.append(f"generated-links: {checked} site-relative URLs resolved")


def check_counts(m) -> None:
    """Any number stated in prose about the manual must match measurement."""
    facts = {
        "sections": m.section_count,
        "diagrams": m.diagram_count,
    }
    checked = 0
    patterns = [
        (r"(\d+)\s+sections", "sections"),
        (r"(\d+)\s+(?:reusable\s+)?diagrams", "diagrams"),
    ]
    for f in [REPO / "README.md", REPO / "MANUAL.md"]:
        text = f.read_text()
        for pat, key in patterns:
            for hit in re.finditer(pat, text):
                checked += 1
                stated = int(hit.group(1))
                if stated != facts[key]:
                    ctx = text[max(0, hit.start() - 40):hit.end() + 20].replace("\n", " ")
                    fail(f"counts: {f.name} says {stated} {key}, measured {facts[key]} — near: ...{ctx}...")
    require_nonzero("counts", checked, "stated counts")
    SUMMARY.append(f"counts: {checked} stated counts verified ({facts['sections']} sections, {facts['diagrams']} diagrams)")


def check_architecture_diagram() -> None:
    """docs/ARCHITECTURE.md embeds the container diagram and claims it is the
    same one that ships in diagrams/src. It drifted once; now it cannot."""
    import re as _re
    arch = REPO / "docs" / "ARCHITECTURE.md"
    src = REPO / "diagrams" / "src" / "master-architecture.mmd"
    if not arch.exists() or not src.exists():
        fail("architecture: expected docs/ARCHITECTURE.md and the master-architecture source")
        return
    blocks = _re.findall(r"```mermaid\n(.*?)```", arch.read_text(), _re.S)
    require_nonzero("architecture", len(blocks), "mermaid blocks")
    if len(blocks) < 2:
        fail("architecture: expected at least two diagrams in ARCHITECTURE.md")
        return
    if blocks[1].strip() != src.read_text().strip():
        fail("architecture: the container diagram in docs/ARCHITECTURE.md no longer matches "
             "diagrams/src/master-architecture.mmd, which it claims to be")
    SUMMARY.append(f"architecture: {len(blocks)} diagrams, container view matches its source")


def check_repo_description(m) -> None:
    """The description lives outside the repository, so no generator can fix it."""
    if os.environ.get("SKIP_REPO_DESCRIPTION"):
        SUMMARY.append("description: skipped (SKIP_REPO_DESCRIPTION set)")
        return
    try:
        out = subprocess.run(
            ["gh", "repo", "view", "--json", "description", "--jq", ".description"],
            capture_output=True, text=True, timeout=30, cwd=REPO,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        SUMMARY.append("description: skipped (gh unavailable)")
        return
    if out.returncode != 0:
        SUMMARY.append("description: skipped (gh not authenticated)")
        return
    desc = out.stdout.strip()
    if not desc:
        fail("description: the repository has no description")
        return
    for pat, actual, label in [
        (r"(\d+)\s+sections", m.section_count, "sections"),
        (r"(\d+)\s+diagrams", m.diagram_count, "diagrams"),
    ]:
        hit = re.search(pat, desc)
        if hit and int(hit.group(1)) != actual:
            fail(f"description: GitHub description says {hit.group(1)} {label}, repository has {actual}. "
                 f"Fix with: gh repo edit --description ...")
    SUMMARY.append(f"description: checked against {m.section_count} sections, {m.diagram_count} diagrams")


def main() -> int:
    m = load()
    check_anchors(m)
    check_relative_files()
    check_generated_site_links()
    check_counts(m)
    check_architecture_diagram()
    check_repo_description(m)

    for line in SUMMARY:
        print(f"  {line}")
    if FAILURES:
        print(f"\n{len(FAILURES)} problem(s):", file=sys.stderr)
        for f in FAILURES:
            print(f"  - {f}", file=sys.stderr)
        return 1
    print("\nall invariants hold")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
