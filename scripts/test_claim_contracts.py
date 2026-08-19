#!/usr/bin/env python3
"""Golden-string regression pins for wording that has drifted before.

This is not a proof that every sentence in the repository is sourced. It pins
the scoped claims that previously escaped a substring check. Coverage of the
tracked set is stated in docs/VERIFICATION.md.
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
    "guardrails": REPO / "docs" / "layers" / "10-guardrails-and-evals.md",
    "architecture": REPO / "docs" / "ARCHITECTURE.md",
    "readme": REPO / "README.md",
    "contributing": REPO / "CONTRIBUTING.md",
}
TEXT = {name: " ".join(path.read_text(encoding="utf-8").split()) for name, path in FILES.items()}
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
        ("pgvector 10M threshold is marked indicative", includes("manual", "comfortable to around 10M vectors")
         and includes("rag", "comfortable to around 10M vectors")),
        ("reranking is not universal", excludes("rag", "single highest-leverage quality add")),
        ("OWASP uses official ASI names", includes("manual", "Agent Goal Hijack")
         and includes("manual", "Rogue Agents") and excludes("manual", "Goal hijacking / prompt injection")),
        ("ADK language list is complete", includes("manual", "Python, TypeScript, Go, Java, and Kotlin")),
        ("ROCm 6.4 is not excluded", includes("manual", "ROCm 6.4 remains available for supported older PyTorch builds")),
        ("code-agent descriptions avoid ranking claims", excludes("manual", "Tops current rankings")
         and excludes("manual", "The most autonomous of the group")),
        ("Codex plan access is accurately scoped", includes("manual", "Included with eligible ChatGPT plans")
         and excludes("manual", "| **Codex CLI** | Paid |")
         and includes("manual", "https://developers.openai.com/codex/pricing")
         and excludes("manual", "https://help.openai.com/en/articles/11369540-using-codex-with-your-chatgpt-plan")),
        ("Copilot is not a single-model service", includes("manual", "Multiple models, plan and surface dependent")),
        ("volatile-source coverage is scoped", includes("manual", "tracked set of volatile model and tool claims")
         and includes("manual", "records primary sources for a tracked set of volatile claims")
         and excludes("manual", "Every volatile claim in this manual traces")
         and excludes("manual", "links every volatile claim to its primary source")
         and excludes("readme", "Every factual claim carries its basis")
         and includes("contributing", "pins a tracked set of those claims as a regression check")
         and excludes("contributing", "every factual claim in `MANUAL.md` traces to a primary source")),
        ("licence tags carry a last-verified date", includes("manual", "16 August 2026")
         and includes("models", "16 August 2026")
         and "Last verified" in TEXT["manual"]
         and "Last verified" in TEXT["models"]),
        ("DeepSeek V4 Flash pricing claim matches the live rate card", excludes("manual", "now opens the first-API-call guide")
         and excludes("manual", "no longer publishes a rate card")
         and excludes("manual", "former pricing URL")
         and excludes("manual", "former docs URL")
         and excludes("manual", "$0.14 in / $0.28 out per M tokens, increase announced")
         and excludes("manual", "$0.14 in on a cache miss")
         and includes("manual", "$0.22-0.44 per 1M tokens for cache-miss input and $0.66-1.32 per 1M tokens for output")
         and includes("manual", "as of 19 August 2026")),
        ("Continue is read-only in the manual and the layer guide", includes("manual", "Read-only since 2026")
         and includes("code_agents", "Read-only since 2026")),
        ("layer red-team gate is policy-scoped", includes("guardrails", "when your release policy requires it")
         and excludes("guardrails", "block release on failure.")),
        ("architecture follows section 27 for named models", includes("architecture", "Named models, licences, and the memory catalogue follow")
         and includes("architecture", "Hermes Agent")),
        ("gpt-oss 120b size is the card figure", includes("manual", "117B total / 5.1B active for 120b")),
        ("Cursor Pro price is dated", includes("manual", "https://cursor.com/pricing")
         and includes("manual", "$20/mo Pro as of 16 August 2026")),
        ("own loop is the open-weight SDK default", includes("manual", "The starred path in the figure is **your own loop**")),
        ("GLM-4.5-Air is not a 16 GB fast tier", includes("manual", "does not belong on the NVIDIA 16-24 GB row")),
        ("Qwen 3.8 27B is downloadable", includes("manual", "Qwen 3.8 27B (downloadable Apache-2.0")
         and includes("models", "Qwen3.8-27B")),
        ("Qwen 3.8 Max weights claim matches the Hub", includes("manual", "Qwen3.8-2.4T-A95B")
         and includes("models", "Qwen3.8-2.4T-A95B")
         and excludes("manual", "no published weights")
         and excludes("manual", "no downloadable weights")
         and excludes("models", "No published weights")),
        ("model layer file is under contract", includes("model_layer", "MODELS.md")),
        ("gpt-oss pin is load-bearing", "117B total / 5.1B active for 120b" in TEXT["manual"]
         and "117B total / 5.1B active for 120b" not in TEXT["manual"].replace(
             "117B total / 5.1B active for 120b", "")),
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
