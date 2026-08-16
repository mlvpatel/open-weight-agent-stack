#!/usr/bin/env python3
"""Keep the deployment-memory catalogue and its safety boundaries explicit.

Run: python3 scripts/test_memory_catalogue.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
FILES = {
    "manual": REPO / "MANUAL.md",
    "layer": REPO / "docs" / "layers" / "09-memory-and-cache.md",
    "architecture": REPO / "docs" / "ARCHITECTURE.md",
    "diagram": REPO / "diagrams" / "src" / "technology-catalogue.mmd",
}
TEXT = {name: " ".join(path.read_text(encoding="utf-8").split()) for name, path in FILES.items()}
FAILURES: list[str] = []

SYSTEMS = {
    "Hermes Agent": {
        "url": "https://hermes-agent.nousresearch.com/docs/user-guide/features/memory",
        "role": "bounded runtime-managed context",
    },
    "Claude-Mem": {
        "url": "https://github.com/thedotmack/claude-mem",
        "role": "hook-based developer-session capture",
    },
    "MemPalace": {
        "url": "https://github.com/MemPalace/mempalace",
        "role": "local-first verbatim structured retrieval",
    },
    "GBrain": {
        "url": "https://github.com/garrytan/gbrain",
        "role": "structured/provenance-aware institutional memory",
    },
    "MemSearch": {
        "url": "https://github.com/zilliztech/memsearch",
        "role": "Markdown source of truth plus hybrid/Milvus derived index",
    },
    "Mem0": {
        "url": "https://github.com/mem0ai/mem0",
        "role": "managed or self-hosted extracted-memory lifecycle",
    },
}

SECURITY_CONTRACT = (
    "retrieved memory is untrusted data, never instructions",
    "hooks and MCP inherit tool authority",
    "provenance, corroboration, quarantine",
    "principal and tenant scoping",
    "local-first is configuration-specific",
    "provider and telemetry egress",
    "decay, expiration, and index reset are not verified deletion",
    "canonical sources and derived indexes, caches, traces, backups, and provider copies",
)

SYSTEM_REVIEWS = {
    "Hermes Agent": "provider-specific egress and deletion",
    "Claude-Mem": "hook capture, model-provider egress, and telemetry",
    "MemPalace": "verbatim retention, stale content, and index maintenance",
    "GBrain": "deployment version, OAuth/source isolation, and exposed MCP",
    "MemSearch": "canonical Markdown deletion and per-project collection separation",
    "Mem0": "managed versus self-hosted data paths, entity filters, and verified deletion",
}


def check(name: str, condition: bool, detail: str = "") -> None:
    if condition:
        print(f"  pass  {name}")
    else:
        print(f"  FAIL  {name}{(': ' + detail) if detail else ''}")
        FAILURES.append(name)


def includes(file: str, phrase: str) -> bool:
    return phrase.casefold() in TEXT[file].casefold()


def contains(text: str, phrase: str) -> bool:
    return phrase.casefold() in text.casefold()


def section(file: str, start: str, end: str | None = None) -> str:
    """Return one required section, or empty text when either boundary is absent."""
    text = TEXT[file]
    if start not in text:
        return ""
    body = text.split(start, 1)[1]
    if end is None:
        return body
    if end not in body:
        return ""
    return body.split(end, 1)[0]


def main() -> int:
    print("memory catalogue contracts:")
    manual_catalogue = section(
        "manual",
        "### 12.1 Deployment memory catalogue",
        "### 12.2 Deployment memory safety and lifecycle boundary",
    )
    manual_security = section(
        "manual",
        "### 12.2 Deployment memory safety and lifecycle boundary",
        "## 13. Guardrails, evals and the improvement loop",
    )
    source_table = section("manual", "### 27.7 Deployment memory catalogue")
    stack_overview = section(
        "manual", "## 3. The thirteen-layer stack", "## 4. The design method"
    )
    layer_matrix = section(
        "layer", "## Deployment memory decision matrix", "## Storage and cache primitives"
    )
    layer_security = section("layer", "## Wiring, security, and lifecycle policy")
    architecture_summary = section(
        "architecture", "## Level 2: containers", "## Level 3: components"
    )
    required_sections = {
        "manual catalogue": manual_catalogue,
        "manual security boundary": manual_security,
        "manual source table": source_table,
        "layer 9 overview": stack_overview,
        "layer decision matrix": layer_matrix,
        "layer security policy": layer_security,
        "architecture summary": architecture_summary,
    }
    for name, body in required_sections.items():
        check(f"required section exists: {name}", bool(body.strip()))

    for system, contract in SYSTEMS.items():
        check(f"manual catalogue includes {system}", contains(manual_catalogue, system)
              and contains(manual_catalogue, contract["url"])
              and contains(manual_catalogue, contract["role"]))
        check(f"layer decision matrix includes {system}", contains(layer_matrix, system)
              and contains(layer_matrix, contract["url"])
              and contains(layer_matrix, contract["role"]))
        check(f"architecture summary includes {system}", contains(architecture_summary, system)
              and contains(architecture_summary, contract["role"]))
        check(f"source table includes {system}'s canonical source",
              contains(source_table, contract["url"]))
        check(f"layer 9 overview names {system}", contains(stack_overview, system))
        check(f"technology catalogue names {system}", includes("diagram", system))
        check(f"layer matrix states {system}'s deployment review",
              contains(layer_matrix, SYSTEM_REVIEWS[system]))

    check("technology catalogue styles every memory node",
          includes("diagram", "ME3,ME4,ME5,ME6,ME7,ME8")
          and all(includes("diagram", f"ME{index}[") for index in range(1, 9)))
    check("storage and cache primitives are not presented as the engine comparison",
          includes("layer", "## Storage and cache primitives")
          and not includes("layer", "## The options"))
    check("primary source table includes Hermes providers documentation",
          contains(source_table, "https://hermes-agent.nousresearch.com/docs/user-guide/features/memory-providers"))
    check("primary source table includes Claude-Mem architecture and telemetry",
          contains(source_table, "https://docs.claude-mem.ai/architecture/overview")
          and contains(source_table, "https://docs.claude-mem.ai/telemetry"))
    check("primary source table includes GBrain protocol",
          contains(source_table, "https://github.com/garrytan/gbrain/blob/master/docs/protocol/MEMORY_VERBS_v1.md"))
    check("primary source table includes MemSearch architecture",
          contains(source_table, "https://zilliztech.github.io/memsearch/architecture/"))
    check("primary source table includes Mem0 lifecycle sources",
          contains(source_table, "https://docs.mem0.ai/core-concepts/memory-operations/add")
          and contains(source_table, "https://docs.mem0.ai/platform/features/memory-expiration"))

    for phrase in SECURITY_CONTRACT:
        check(f"manual security boundary says: {phrase}", contains(manual_security, phrase))
        check(f"layer security policy says: {phrase}", contains(layer_security, phrase))

    catalogue_text = " ".join(
        (manual_catalogue, layer_matrix)
    )
    banned = re.compile(
        r"\b(?:always-on|perfect recall|smart forgetting|injection-proof|poisoning-proof|"
        r"tenant-safe|private by default|zero telemetry|compliant|production-ready|"
        r"highest-scoring|best)\b",
        re.IGNORECASE,
    )
    check("catalogue descriptions avoid unsupported absolutes and superlatives",
          banned.search(catalogue_text) is None)

    if FAILURES:
        print(f"\n{len(FAILURES)} contract(s) failed", file=sys.stderr)
        return 1
    print("\nall memory catalogue contracts pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
