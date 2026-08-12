# Changelog

## 1.1.1 - 2026-08-11 (local release candidate)

**README architecture hero.** The cropped website screenshot is replaced by a
compact light-theme request-and-answer map that remains readable at GitHub's
rendered width, with automated checks for dimensions, weight, alt text, visible
copy, theme, and stale-asset removal. Its lead copy now states the stack's hybrid
open-weight and hosted-model scope explicitly.

**Deployment memory catalogue.** The manual and Layer 9 now distinguish six deployment-memory
roles and document their source links, write gates, authority inheritance, egress review, and
end-to-end erasure boundaries.

**Published-site integrity.** Repository-local Markdown links are converted to
stable GitHub document URLs in the generated Pages site, and regression checks
now reject generated-site links that would 404 under a repository path.

**Claims and freshness.** Documentation wording was narrowed to supported,
source-linked claims. The upstream watcher now tracks the exact model IDs used
by the manual, distinguishes temporary upstream failures from removals, and
records the review state explicitly.

**Reproducible supply chain and tests.** The CycloneDX SBOM is deterministic,
fresh against the lockfile, schema-validated offline, and checked in CI. The
offline suite has a measured Python coverage gate and protects factual claims,
freshness, generated links, workflow security, and release metadata.

**Browser and workflow hardening.** A sandboxed Chromium gate opens the site
under its GitHub Pages repository path, requires all 18 Mermaid diagrams, and
turns a Mermaid failure into visible safe fallback text. CodeQL is configured
locally for Python and JavaScript/TypeScript; hosted scanning becomes active
only after this candidate is pushed and the workflow runs on GitHub.

**Governance accounting.** Verification and security documentation now name
the actual local gates and distinguish them from GitHub settings that require
owner action after push.

## 1.1.0

Trustworthy and self-maintaining.

**Corrected against primary sources.** Every runtime version floor was wrong or
outdated: Node 20 had reached end of life, the stated Python range matched
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

**Model facts are re-checked after publication.** A weekly watcher compares
licence and availability for the models the manual names against their sources
and reports drift once confirmed across runs.

## 1.0.0

First public release: the full manual with diagrams, primary-source citations, OWASP Agentic Top 10 control mapping, task-to-model routing, databases and versioning chapters, and the first-hour troubleshooting table.
