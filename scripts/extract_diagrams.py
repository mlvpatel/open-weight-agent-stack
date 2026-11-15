#!/usr/bin/env python3
"""Regenerate diagrams/src/*.mmd from MANUAL.md (the single source of truth)."""
from __future__ import annotations

import pathlib
import sys


ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from lib.manual import load  # noqa: E402
from lib.render import FIGURES  # noqa: E402

NAMES = [name for name, _title in FIGURES]


def main() -> int:
    """Extract exactly the manual's diagram blocks in their documented order."""
    blocks = load(ROOT / "MANUAL.md").diagrams
    if len(blocks) != len(NAMES):
        print(f"expected {len(NAMES)} mermaid blocks, found {len(blocks)}: update FIGURES in scripts/lib/render.py")
        return 1
    output = ROOT / "diagrams" / "src"
    output.mkdir(parents=True, exist_ok=True)
    for name, block in zip(NAMES, blocks):
        (output / f"{name}.mmd").write_text(block, encoding="utf-8")
    print(f"wrote {len(blocks)} diagrams to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
