#!/usr/bin/env python3
"""Regenerate diagrams/src/*.mmd from MANUAL.md (the single source of truth)."""
import re, pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent
NAMES = ["hardware-paths","master-architecture","request-lifecycle","agent-control-loop",
         "rag-pipeline","model-routing","prompt-contract","trust-boundaries","memory-tiers",
         "guardrails-evals","deployment-topology","data-lifecycle","serving-budgets",
         "identity-delegation","threat-write-paths","latency-budget","technology-catalogue",
         "platform-sdk"]
md = (ROOT / "MANUAL.md").read_text()
blocks = re.findall(r"```mermaid\n(.*?)```", md, re.S)
if len(blocks) != len(NAMES):
    raise SystemExit(f"expected {len(NAMES)} mermaid blocks, found {len(blocks)}: update NAMES")
out = ROOT / "diagrams" / "src"
out.mkdir(parents=True, exist_ok=True)
for name, block in zip(NAMES, blocks):
    (out / f"{name}.mmd").write_text(block)
print(f"wrote {len(blocks)} diagrams to {out}")
