# What verification does and does not prove

This manual claims its facts are checkable. That claim is only useful if you know exactly what is checked, by what, and what is left to human judgement. This page is that accounting.

## The evidence convention

Three levels appear throughout the manual, and the distinction is deliberate.

| Marker | Meaning | Example |
|---|---|---|
| A plain number or claim | Sourced or derivable. A link in [section 27](../MANUAL.md#27-sources-and-verification) supports it, or the arithmetic that produces it is shown | A 32B model needs 16 to 18 GB at 4-bit |
| `reported` | Attributed to a named party who measured it. The manual repeats their figure and names them; it has not reproduced the measurement | SGLang reports up to 5 times higher throughput |
| `indicative` | An engineering heuristic with no published source. Useful for planning, not a measurement, and your hardware may differ | pgvector is comfortable to around 10M vectors, then measure |

A claim with no marker and no source is a defect. Report it.

## What CI verifies automatically

Four deterministic jobs (`diagrams`, `generated`, `browser`, `invariants`) run on every push to `main`, on every pull request, and weekly on a schedule. Their result depends only on the commit. The Pages deployment runs for a push to `main` or a manual run on `main`, and waits for all four. Checks that depend on the network or the calendar (`links` and `drift`) do not gate the deployment, so a third-party outage or a date cannot block a fix. A failed scheduled run opens or updates a GitHub issue.

**`diagrams`**
- `diagrams/src` matches what the manual currently contains, so the extracted sources cannot go stale.

**`generated`**
- The vendored Mermaid browser bundle is compared byte-for-byte against the version pinned in the lockfile.
- `site/index.html`, `site/architecture.html`, and `site/models.html` are regenerated from `MANUAL.md`, `docs/ARCHITECTURE.md`, and `docs/MODELS.md`, and the build fails if a committed copy differs.
- The regenerated document is valid HTML.

**`browser`**
- The generated site is opened in Chromium.
- All 20 Mermaid diagrams must render as visible SVGs.
- Browser console and page errors, failed local requests, unloaded images, and deploy-unsafe links fail the gate.
- A synthetic Mermaid bundle/run failure must produce visible safe fallback text for every diagram and a useful console error rather than being silently swallowed.
- Repository-relative documentation links are rejected in the generated site because GitHub Pages serves from a repository path, not the repository root.

**`invariants`**
- `npm test` runs the renderer-injection, factual-claim, generated-link, freshness, coverage, workflow-security, and release-metadata regression contracts.
- Every internal `MANUAL.md#anchor` reference resolves to a real heading.
- Every relative link between repository files points at a file that exists.
- Every count stated in prose matches the measured value.
- Each check reports how many items it inspected and fails when it inspected none.
- A separate step breaks an anchor on purpose and fails if the checker still passes.

The claim-contract suite is a golden-string pin on wording that has drifted, not a proof that every sentence is sourced. It currently runs more than 30 pins across MANUAL.md, MODELS.md, README.md, CONTRIBUTING.md, and the layer guides. Model-card licence coverage for `automated_models` in `.github/freshness-sources.json` is mechanically complete.

Section 27.1 through 27.3 together hold 54 evidence-table rows. Of those, 9 are backed by at least one pinned check above: the Qwen 2/2.5, DeepSeek V4 Pro, DeepSeek V4 Flash, GLM-5.2, GLM-4.5-Air, MiniMax M2.7, gpt-oss-120b/20b, and Qwen 3.8 27B rows in 27.1, plus the OWASP Top 10 for Agentic Applications row in 27.3. The other 45 rows carry no automated pin and rely on the human-sampling process documented in [HUMAN-REVIEW.md](HUMAN-REVIEW.md).

**`links`** (pull requests, weekly schedule, manual runs; not a deploy gate)
- Every external link in the manual, README, and docs returns a genuine success status. Rate-limited and forbidden responses are not accepted as success.

**`drift`** (weekly schedule and manual runs; not a deploy gate)
- Last-verified dates must be parseable and younger than 45 days.
- The freshness watcher wrote its `last_run` heartbeat within the last 14 days.
- The GitHub repository description agrees with the repository. That description lives outside the repository, so no generator can fix it.
- package.json must match the latest GitHub release tag when `gh` can see one.

The `codeql` workflow scans Python and JavaScript/TypeScript on pushes, pull requests, weekly schedules, and manual dispatch. Branch protection on `main` requires `Analyze (python)`, `Analyze (javascript-typescript)`, and `CodeQL`.

The `freshness` workflow runs weekly and is not a gate: it compares the manual's model claims against their sources and opens a pull request when they drift. See [FRESHNESS.md](FRESHNESS.md).

## What CI does not verify

This is the part that matters, and the part most repositories leave unsaid.

- **Whether a source supports the claim it is cited for.** A link can resolve perfectly while pointing at a page that says something different, or nothing relevant at all. Only a human reading both can catch that.
- **Whether a resolving link still shows the same content.** Model cards get edited. Licences change. A URL that worked yesterday may describe a different licence today and still return a success status. The freshness watcher covers licence and gating changes for a named set of models; it does not cover prose.
- **Whether a number is current.** Parameter counts, benchmark scores, prices, and version floors move. A stale number is invisible to a link checker. Section 27 and `docs/MODELS.md` carry a human **Last verified** date for the named Hugging Face licence tags.
- **Whether a recommendation is good.** Rankings, "best for" columns, and suggested defaults are editorial judgement informed by research. They are argued, not proven.
- **Whether an `indicative` heuristic holds on your hardware.** It is a starting point for capacity planning, not a guarantee.
- **Whether prose in `docs/` agrees with prose in the manual.** CI now fails if a layer file is missing or the index table drifts. It still cannot prove that a layer guide's wording matches the manual. The architecture document's container diagram is compared to `diagrams/src`; its surrounding prose is not.
- **Whether branch-protection trade-offs are accepted.** Required checks on `main` are `diagrams`, `generated`, `invariants`, `browser`, `Analyze (python)`, `Analyze (javascript-typescript)`, and `CodeQL`. Required signatures, administrator enforcement, linear history, and conversation resolution are off, while force pushes and branch deletions are disabled.

## What this means for you as a reader

Treat the manual as a well-sourced starting point, not an oracle. For any decision that carries real cost, follow the link in [section 27](../MANUAL.md#27-sources-and-verification) and read the primary source. That is why every volatile claim carries one.

The claims most worth checking yourself before committing money or architecture: model licences, because they are legal guidance by implication and change without notice; benchmark figures, because they are frequently reported for a different model variant or a different reasoning mode than the one named; and anything marked `indicative`.

## What this means for you as a contributor

A correction needs a primary source: a model card, a licence file, official documentation, or a paper. News articles, blog roundups, and social posts do not qualify, because they are themselves uncited summaries.

If you find a claim whose source does not support it, that is the most valuable issue you can open. Automation cannot find those.

## Keeping this page honest

This page describes the checks that exist today. It has been wrong before: an earlier version listed two gates when five jobs were running, and asserted it was a complete list. If you find a gap between what this page claims and what `.github/workflows/` actually runs, that gap is a defect worth reporting.
