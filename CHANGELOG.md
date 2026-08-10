# Changelog

## 1.1.0

Trustworthy and self-maintaining.

**Corrected against primary sources.** Every runtime version floor was wrong or
outdated: Node 20 had reached end of life, the stated Python range excluded
neither runtime's real floor, the CUDA driver rule misstated minor-version
compatibility, and ROCm was three major versions behind. Licences are now
stated per model rather than per family, because five of seven families ship
different terms to different models. Qwen 3.8 Max is marked API-only after
verification found no published weights. The DeepSeek SWE-bench figure is
attributed to its reasoning mode rather than a model that does not exist.
Discontinued coding agents are marked with their successors.

**Claims aligned with evidence.** Absolute security guarantees became statements
of what the controls deliver. An evidence convention distinguishes sourced
numbers, attributed figures, and unsourced heuristics. docs/VERIFICATION.md
states plainly what CI does and does not prove.

**The site is generated.** site/index.html is produced from MANUAL.md and CI
fails when the committed copy differs, so hand-syncing cannot reintroduce drift.
The published document is now valid HTML with a viewport, which it never had.

**The build is reproducible.** Dependencies are pinned by lockfile, Actions by
commit SHA, and diagram rendering is byte-identical across runs.

**Facts are re-checked after publication.** A weekly watcher compares the
manual's model claims against their sources and proposes corrections.

## 1.0.0

First public release: the full manual with diagrams, primary-source citations, OWASP Agentic Top 10 control mapping, task-to-model routing, databases and versioning chapters, and the first-hour troubleshooting table.
