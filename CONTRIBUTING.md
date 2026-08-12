# Contributing

This manual holds one line: every factual claim traces to a primary source.

## Corrections (most valuable)

Open an issue with the correction template, or a PR that edits `MANUAL.md`. A correction needs:

1. The current text, quoted exactly.
2. The corrected text.
3. A primary source: model card, licence file, official docs, or paper. News posts and blog roundups do not qualify.

## Ground rules

- `MANUAL.md` is the single source of truth. `site/index.html` and `diagrams/` derive from it.
- Diagram edits happen in the manual's mermaid blocks; run `scripts/extract_diagrams.py` after.
- New tools or models enter with multiple options per category, never as the single answer.
- No em dashes, no section symbols, sentence-case headings.
- CI must pass: all diagrams compile, all links resolve.

## AI-assisted contributions

Disclose material AI assistance in the pull-request description. If an
assistant is being recognised across the project rather than for one change,
update `CONTRIBUTORS.md` with its role and the evidence for that attribution.

The human contributor must verify every generated claim, source, test, and code
change before submission. Do not use an unrelated GitHub account, a fabricated
email address, an empty commit, or rewritten history to make an AI tool appear
in GitHub's native Contributors graph.

## What gets declined

Cost-of-service debates (the manual is performance-first by design), vendor advocacy without comparative basis, and claims without a checkable source.
