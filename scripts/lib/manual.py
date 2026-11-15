#!/usr/bin/env python3
"""One parse of MANUAL.md, shared by every generator and every checker.

Nothing else in this repository is allowed to parse the manual. Generators
write derived files from this model; checkers read from it. A checker that
re-parses independently can disagree with the generator, which is how the
counts drifted to three different values in the first place.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
MANUAL = REPO / "MANUAL.md"


def slug(heading: str) -> str:
    """GitHub's anchor slug for a heading."""
    s = heading.strip().lower()
    s = re.sub(r"[^\w\s-]", "", s)
    return re.sub(r"\s+", "-", s)


@dataclass
class Manual:
    text: str
    headings: list[tuple[int, str]] = field(default_factory=list)
    anchors: set[str] = field(default_factory=set)
    diagrams: list[str] = field(default_factory=list)
    links: list[str] = field(default_factory=list)
    sections: list[str] = field(default_factory=list)

    @property
    def link_count(self) -> int:
        return len(self.links)

    @property
    def unique_links(self) -> int:
        return len(set(self.links))

    @property
    def diagram_count(self) -> int:
        return len(self.diagrams)

    @property
    def section_count(self) -> int:
        return len(self.sections)


# The one fence grammar: 3+ backticks open a block, and the same run alone on a
# line closes it. Groups: marker, info string, body (with its final newline).
FENCE = re.compile(r"^(`{3,})(.*?)\n(.*?)^\1[ \t]*$", re.M | re.S)


def split_fences(text: str) -> list[tuple[re.Match[str] | None, str]]:
    """Cut text into prose and fenced chunks, in order; a fenced chunk carries its match."""
    parts: list[tuple[re.Match[str] | None, str]] = []
    cursor = 0
    for fence in FENCE.finditer(text):
        parts.append((None, text[cursor:fence.start()]))
        parts.append((fence, fence.group(0)))
        cursor = fence.end()
    parts.append((None, text[cursor:]))
    return parts


def mask_fences(text: str) -> str:
    """Blank fenced code, keeping line numbers, so it never registers as headings or links."""
    return FENCE.sub(lambda fence: "\n" * fence.group(0).count("\n"), text)


def load(path: Path | None = None) -> Manual:
    path = path or MANUAL
    text = path.read_text(encoding="utf-8")
    masked = mask_fences(text)

    headings = [
        (len(m.group(1)), m.group(2).strip())
        for m in re.finditer(r"^(#{1,4})\s+(.+)$", masked, re.M)
    ]
    sections = [h for lvl, h in headings if lvl == 2 and re.match(r"^\d+\.", h)]

    return Manual(
        text=text,
        headings=headings,
        anchors={slug(h) for _, h in headings},
        diagrams=[f.group(3) for f in FENCE.finditer(text) if f.group(2).strip() == "mermaid"],
        links=re.findall(r"\]\((https?://[^)]+)\)", masked),
        sections=sections,
    )


def markdown_files() -> list[Path]:
    """Every markdown file in the repository, excluding vendored trees."""
    skip = {".git", "node_modules", "site"}
    out = []
    for p in REPO.rglob("*.md"):
        if any(part in skip for part in p.parts):
            continue
        out.append(p)
    return sorted(out)
