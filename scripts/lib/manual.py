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


def load(path: Path | None = None) -> Manual:
    path = path or MANUAL
    text = path.read_text()

    # Mask fenced code so its contents never register as headings or links.
    masked = re.sub(r"```.*?```", lambda m: "\n" * m.group(0).count("\n"), text, flags=re.S)

    headings = [
        (len(m.group(1)), m.group(2).strip())
        for m in re.finditer(r"^(#{1,4})\s+(.+)$", masked, re.M)
    ]
    sections = [h for lvl, h in headings if lvl == 2 and re.match(r"^\d+\.", h)]

    m = Manual(
        text=text,
        headings=headings,
        anchors={slug(h) for _, h in headings},
        diagrams=re.findall(r"```mermaid\n(.*?)```", text, re.S),
        links=re.findall(r"\]\((https?://[^)]+)\)", masked),
        sections=sections,
    )
    return m


def markdown_files() -> list[Path]:
    """Every markdown file in the repository, excluding vendored trees."""
    skip = {".git", "node_modules", "site"}
    out = []
    for p in REPO.rglob("*.md"):
        if any(part in skip for part in p.parts):
            continue
        out.append(p)
    return sorted(out)
