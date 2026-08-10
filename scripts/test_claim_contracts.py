#!/usr/bin/env python3
"""Guard evidence-sensitive manual claims against unsupported absolutes.

The manual links to primary sources, but words such as "always", "any", and
"the best" can accidentally turn a useful recommendation into a false promise.
This compact contract pins the scoped wording used for the claims that have
previously drifted.  Run: python3 scripts/test_claim_contracts.py
"""
from __future__ import annotations

import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
FILES = {
    "manual": REPO / "MANUAL.md",
    "models": REPO / "docs" / "MODELS.md",
    "rag": REPO / "docs" / "layers" / "05-rag-pipeline.md",
    "model_layer": REPO / "docs" / "layers" / "06-model-layer.md",
    "code_agents": REPO / "docs" / "layers" / "08-code-agent.md",
}
TEXT = {name: " ".join(path.read_text().split()) for name, path in FILES.items()}
FAILURES: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    if condition:
        print(f"  pass  {name}")
    else:
        print(f"  FAIL  {name}{(': ' + detail) if detail else ''}")
        FAILURES.append(name)


def includes(file: str, phrase: str) -> bool:
    return phrase in TEXT[file]


def excludes(file: str, phrase: str) -> bool:
    return phrase not in TEXT[file]


def main() -> int:
    print("claim accuracy contracts:")
    checks = [
        ("Qwen licence scope is consistent", includes("manual", "Qwen 2 and 2.5 are generally Apache-2.0")
         and includes("models", "Qwen 2 and 2.5, most sizes")),
        ("intro licences name exact checkpoints", includes("manual", "MiniMax M2.7 requires prior written authorisation for commercial use")
         and includes("manual", "DeepSeek V4 Pro / V4 Flash and GLM-5.2 / GLM-4.5-Air checkpoints are MIT")
         and excludes("manual", "DeepSeek and GLM release under MIT")),
        ("Mermaid promise names compatible viewers", includes("manual", "compatible Mermaid viewer")),
        ("sizing estimates declare assumptions", includes("manual", "illustrative estimates")
         and includes("manual", "architecture, KV-head count, precision, batch, and context length")),
        ("quantisation quality is conditional", excludes("manual", "AWQ usually holds quality better")
         and excludes("manual", "Near-lossless; the serving default")),
        ("prompt ordering is a mitigation", includes("manual", "can help attention")
         and excludes("manual", "where attention is strongest")),
        ("model cannot be trusted to distinguish data", includes("manual", "do not make a model reliably distinguish")),
        ("hosted sandbox is not equated to an API", excludes("manual", "same isolation as an API")),
        ("red-team CI is policy-scoped", includes("manual", "when your release policy requires it")
         and excludes("manual", "Any failure blocks release")),
        ("prefill/decode split is qualified", includes("manual", "can improve isolation and tail inter-token latency")
         and excludes("manual", "Batching them together makes both worse.")),
        ("retention is policy and legal-basis dependent", includes("manual", "retention policy, legal basis, and deletion commitments")),
        ("CPU chat is possible but limited", excludes("manual", "Interactive chat needs a GPU")
         and includes("manual", "CPU-only chat is possible")),
        ("pgvector has no hard vector ceiling", excludes("manual", "comfortably to around 10M vectors")
         and includes("rag", "Measure against your workload")),
        ("reranking is not universal", excludes("rag", "single highest-leverage quality add")),
        ("OWASP uses official ASI names", includes("manual", "Agent Goal Hijack")
         and includes("manual", "Rogue Agents") and excludes("manual", "Goal hijacking / prompt injection")),
        ("ADK language list is complete", includes("manual", "Python, TypeScript, Go, Java, and Kotlin")),
        ("ROCm 6.4 is not excluded", includes("manual", "ROCm 6.4 remains available for supported older PyTorch builds")),
        ("code-agent descriptions avoid ranking claims", excludes("manual", "Tops current rankings")
         and excludes("manual", "The most autonomous of the group")),
        ("Codex plan access is accurately scoped", includes("manual", "Included with eligible ChatGPT plans")
         and excludes("manual", "| **Codex CLI** | Paid |")),
        ("Copilot is not a single-model service", includes("manual", "Multiple models, plan and surface dependent")),
        ("volatile-source coverage is scoped", includes("manual", "tracked set of volatile model and tool claims")
         and includes("manual", "records primary sources for a tracked set of volatile claims")
         and excludes("manual", "Every volatile claim in this manual traces")
         and excludes("manual", "links every volatile claim to its primary source")),
    ]
    for name, passed in checks:
        check(name, passed)
    if FAILURES:
        print(f"\n{len(FAILURES)} contract(s) failed", file=sys.stderr)
        return 1
    print("\nall claim accuracy contracts pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
