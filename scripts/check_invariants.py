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

import json
import os
import re
import subprocess
import sys
from datetime import date
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
        text = f.read_text(encoding="utf-8")
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
        for ref in re.finditer(r"\]\(([^)#]+\.(?:md|png|json|svg))(?:#[^)]*)?\)", f.read_text(encoding="utf-8")):
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
    site_root = (REPO / "site").resolve()
    pages = sorted(
        p for p in site_root.glob("*.html")
        if p.is_file() and p.name != "template.html"
    )
    if not pages:
        fail("generated-links: expected generated HTML under site/")
        return

    collector = _GeneratedURLCollector()
    for page in pages:
        collector.feed(page.read_text(encoding="utf-8"))
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
    leftover_pages = 0
    for page in pages:
        leftover_pages += 1
        leftovers = re.findall(r"\{\{[A-Z_]+\}\}", page.read_text(encoding="utf-8"))
        if leftovers:
            fail(f"generated-links: {page.name} still has placeholders {sorted(set(leftovers))}")
    require_nonzero("generated-placeholders", leftover_pages, "generated HTML pages")
    SUMMARY.append(f"generated-links: {checked} site-relative URLs resolved, {leftover_pages} pages free of placeholders")


def check_counts(m) -> None:
    """Any number stated in prose about the manual must match measurement."""
    facts = {
        "sections": m.section_count,
        "diagrams": m.diagram_count,
        "unique_links": m.unique_links,
        "links": m.link_count,
    }
    checked = 0
    patterns = [
        (r"(\d+)\s+sections", "sections"),
        (r"(\d+)\s+(?:reusable\s+)?diagrams", "diagrams"),
        (r"(\d+)\s+Mermaid diagrams", "diagrams"),
        (r"(\d+)\s+primary sources", "unique_links"),
        (r"(\d+)\s+unique sources", "unique_links"),
    ]
    files = [
        REPO / "README.md",
        REPO / "MANUAL.md",
        REPO / "docs" / "VERIFICATION.md",
        REPO / "CHANGELOG.md",
    ]
    for f in files:
        text = f.read_text(encoding="utf-8")
        for pat, key in patterns:
            for hit in re.finditer(pat, text):
                checked += 1
                stated = int(hit.group(1))
                if stated != facts[key]:
                    ctx = text[max(0, hit.start() - 40):hit.end() + 20].replace("\n", " ")
                    fail(f"counts: {f.name} says {stated} {key}, measured {facts[key]} — near: ...{ctx}...")
    require_nonzero("counts", checked, "stated counts")
    SUMMARY.append(
        f"counts: {checked} stated counts verified ({facts['sections']} sections, "
        f"{facts['diagrams']} diagrams, {facts['unique_links']} unique sources)"
    )


MONTHS = {
    "January": 1, "February": 2, "March": 3, "April": 4, "May": 5, "June": 6,
    "July": 7, "August": 8, "September": 9, "October": 10, "November": 11, "December": 12,
}
LAST_VERIFIED_MAX_AGE_DAYS = 45


def check_last_verified() -> None:
    """A pinned date that never moves is a staleness assertion, not a freshness one."""
    pattern = re.compile(r"Last verified:\*?\*?\s+(\d{1,2}) ([A-Za-z]+) (\d{4})")
    today = date.today()
    checked = 0
    for f in (REPO / "MANUAL.md", REPO / "docs" / "MODELS.md"):
        text = f.read_text(encoding="utf-8")
        hits = list(pattern.finditer(text))
        if not hits:
            fail(f"last-verified: {f.name} has no Last verified date")
            continue
        for hit in hits:
            checked += 1
            day, month_name, year = int(hit.group(1)), hit.group(2), int(hit.group(3))
            month = MONTHS.get(month_name)
            if month is None:
                fail(f"last-verified: {f.name} has unparsable month {month_name!r}")
                continue
            verified = date(year, month, day)
            age = (today - verified).days
            if age > LAST_VERIFIED_MAX_AGE_DAYS:
                fail(f"last-verified: {f.name} is {age} days old (limit {LAST_VERIFIED_MAX_AGE_DAYS})")
            if age < 0:
                fail(f"last-verified: {f.name} is dated in the future")
    require_nonzero("last-verified", checked, "dates")
    SUMMARY.append(f"last-verified: {checked} dates within {LAST_VERIFIED_MAX_AGE_DAYS} days")


def check_release_version() -> None:
    """package.json must match the latest GitHub release when one exists."""
    if os.environ.get("SKIP_REPO_DESCRIPTION"):
        SUMMARY.append("release: skipped (SKIP_REPO_DESCRIPTION set)")
        return
    package = json.loads((REPO / "package.json").read_text(encoding="utf-8"))
    version = package.get("version")
    try:
        out = subprocess.run(
            ["gh", "release", "view", "--json", "tagName", "--jq", ".tagName"],
            capture_output=True, text=True, timeout=30, cwd=REPO,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        SUMMARY.append("release: skipped (gh unavailable)")
        return
    if out.returncode != 0:
        SUMMARY.append("release: skipped (no GitHub release or gh not authenticated)")
        return
    tag = out.stdout.strip().lstrip("v")
    def parts(value: str) -> tuple[int, ...]:
        try:
            return tuple(int(piece) for piece in value.split("."))
        except ValueError:
            return ()
    github, local = parts(tag), parts(str(version))
    if not github or not local:
        fail(f"release: GitHub {tag!r} or package.json {version!r} is not dotted numeric")
        return
    if github < local:
        SUMMARY.append(f"release: package {version} is ahead of GitHub {tag} (candidate)")
        return
    if github != local:
        fail(f"release: GitHub release is {tag!r}, package.json is {version!r}")
        return
    SUMMARY.append(f"release: GitHub {tag} matches package.json")


def check_published_trees() -> None:
    """Empty published directories are a shipping defect."""
    checked = 0
    for relative in ("docs/assets", "docs/layers"):
        path = REPO / relative
        checked += 1
        if not path.is_dir():
            fail(f"trees: {relative} is missing")
            continue
        if not any(path.iterdir()):
            fail(f"trees: {relative} is empty")
    require_nonzero("trees", checked, "directories")
    SUMMARY.append(f"trees: {checked} published directories have contents")


def check_evidence_markers() -> None:
    """Evidence-tier words in prose must be backticked so the convention is mechanical."""
    text = (REPO / "MANUAL.md").read_text(encoding="utf-8")
    masked = re.sub(r"```.*?```", lambda match: "\n" * match.group(0).count("\n"), text, flags=re.S)
    checked = 0
    for word in ("indicative", "reported"):
        for hit in re.finditer(rf"\b{word}\b", masked, re.I):
            checked += 1
            before = masked[hit.start() - 1] if hit.start() else ""
            after = masked[hit.end()] if hit.end() < len(masked) else ""
            if before != "`" or after != "`":
                line = masked.count("\n", 0, hit.start()) + 1
                fail(f"evidence: {word!r} on line {line} is not a backticked marker")
    require_nonzero("evidence", checked, "evidence-tier words")
    SUMMARY.append(f"evidence: {checked} indicative/reported uses are backticked")


def check_layer_files() -> None:
    """The thirteen layer guides must exist and match the index table.

    Prose agreement with MANUAL.md is still a human check. This gate only
    stops a missing or renamed file from leaving a dead README link.
    """
    readme = REPO / "docs" / "layers" / "README.md"
    if not readme.exists():
        fail("layers: expected docs/layers/README.md")
        return
    listed = re.findall(r"\[(\d{2}-[a-z0-9-]+\.md)\]", readme.read_text(encoding="utf-8"))
    require_nonzero("layers", len(listed), "layer files in README")
    if len(listed) != 13:
        fail(f"layers: README lists {len(listed)} files, expected 13")
        return
    directory = REPO / "docs" / "layers"
    on_disk = sorted(p.name for p in directory.glob("*.md") if p.name != "README.md")
    expected = sorted(listed)
    if on_disk != expected:
        fail(f"layers: README lists {expected}, directory has {on_disk}")
        return
    for name in listed:
        if not (directory / name).is_file():
            fail(f"layers: {name} is listed but missing")
    SUMMARY.append(f"layers: {len(listed)} files exist and match the index")


def check_architecture_diagram() -> None:
    """docs/ARCHITECTURE.md embeds the container diagram and claims it is the
    same one that ships in diagrams/src. It drifted once; now it cannot."""
    import re as _re
    arch = REPO / "docs" / "ARCHITECTURE.md"
    src = REPO / "diagrams" / "src" / "master-architecture.mmd"
    if not arch.exists() or not src.exists():
        fail("architecture: expected docs/ARCHITECTURE.md and the master-architecture source")
        return
    blocks = _re.findall(r"```mermaid\n(.*?)```", arch.read_text(encoding="utf-8"), _re.S)
    require_nonzero("architecture", len(blocks), "mermaid blocks")
    if len(blocks) < 2:
        fail("architecture: expected at least two diagrams in ARCHITECTURE.md")
        return
    if blocks[1].strip() != src.read_text(encoding="utf-8").strip():
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
    check_last_verified()
    check_layer_files()
    check_architecture_diagram()
    check_published_trees()
    check_evidence_markers()
    check_repo_description(m)
    check_release_version()

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
