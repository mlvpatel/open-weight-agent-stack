#!/usr/bin/env python3
"""Regenerate diagrams/src/*.mmd from MANUAL.md (the single source of truth)."""
from __future__ import annotations

import pathlib
import re


ROOT = pathlib.Path(__file__).resolve().parent.parent
NAMES = ["hardware-paths", "master-architecture", "request-lifecycle", "agent-control-loop",
         "rag-pipeline", "model-routing", "prompt-contract", "trust-boundaries", "memory-tiers",
         "guardrails-evals", "deployment-topology", "data-lifecycle", "serving-budgets",
         "identity-delegation", "threat-write-paths", "latency-budget", "technology-catalogue",
         "platform-sdk"]


def main() -> int:
    """Extract exactly the manual's diagram blocks in their documented order."""
    markdown = (ROOT / "MANUAL.md").read_text()
    blocks = re.findall(r"```mermaid\n(.*?)```", markdown, re.S)
    if len(blocks) != len(NAMES):
        print(f"expected {len(NAMES)} mermaid blocks, found {len(blocks)}: update NAMES")
        return 1
    output = ROOT / "diagrams" / "src"
    output.mkdir(parents=True, exist_ok=True)
    for name, block in zip(NAMES, blocks):
        (output / f"{name}.mmd").write_text(block)
    print(f"wrote {len(blocks)} diagrams to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
