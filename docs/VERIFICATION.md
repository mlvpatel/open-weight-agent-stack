# What verification does and does not prove

This manual claims its facts are checkable. That claim is only useful if you know exactly what is checked, by what, and what is left to human judgement. This page is that accounting.

## The evidence convention

Three levels appear throughout the manual, and the distinction is deliberate.

| Marker | Meaning | Example |
|---|---|---|
| A plain number or claim | Sourced or derivable. A link in [section 27](../MANUAL.md#27-sources-and-verification) supports it, or the arithmetic that produces it is shown | A 32B model needs 16 to 18 GB at 4-bit |
| `reported` | Attributed to a named party who measured it. The manual repeats their figure and names them; it has not reproduced the measurement | SGLang reports up to 5 times higher throughput |
| `indicative` | An engineering heuristic with no published source. Useful for planning, not a measurement, and your hardware may differ | Around 10M vectors is where pgvector stops being comfortable |

A claim with no marker and no source is a defect. Report it.

## What CI verifies automatically

Five jobs run on every push to `main`, on every pull request, and weekly on a schedule. Deployment is gated on all five passing.

**`diagrams`**
- Every Mermaid source extracted from the manual compiles.
- `diagrams/src` matches what the manual currently contains, so the extracted sources cannot go stale.
- The renderer produces byte-identical output when run twice, which is what makes the drift gate below meaningful.

**`generated`**
- `site/index.html` is regenerated from `MANUAL.md` and the build fails if the committed copy differs, so the published page cannot drift from its source.
- The regenerated document is valid HTML.

**`invariants`**
- Every internal `MANUAL.md#anchor` reference resolves to a real heading.
- Every relative link between repository files points at a file that exists.
- Every count stated in prose matches the measured value.
- The GitHub repository description agrees with the repository. That description lives outside the repository, so no generator can fix it.
- Each check reports how many items it inspected and fails when it inspected none.
- A separate step breaks an anchor on purpose and fails if the checker still passes.

**`html`**
- A deliberately malformed document is fed to the validator, and the job fails if the validator accepts it.

**`links`**
- Every external link in the manual, README, and docs returns a genuine success status. Rate-limited and forbidden responses are not accepted as success.

A sixth workflow, `freshness`, runs weekly and is not a gate: it compares the manual's model claims against their sources and opens a pull request when they drift. See [FRESHNESS.md](FRESHNESS.md).

## What CI does not verify

This is the part that matters, and the part most repositories leave unsaid.

- **Whether a source supports the claim it is cited for.** A link can resolve perfectly while pointing at a page that says something different, or nothing relevant at all. Only a human reading both can catch that.
- **Whether a resolving link still shows the same content.** Model cards get edited. Licences change. A URL that worked yesterday may describe a different licence today and still return a success status. The freshness watcher covers licence and gating changes for a named set of models; it does not cover prose.
- **Whether a number is current.** Parameter counts, benchmark scores, prices, and version floors move. A stale number is invisible to a link checker.
- **Whether a recommendation is good.** Rankings, "best for" columns, and suggested defaults are editorial judgement informed by research. They are argued, not proven.
- **Whether an `indicative` heuristic holds on your hardware.** It is a starting point for capacity planning, not a guarantee.
- **Whether prose in `docs/` agrees with prose in the manual.** Only the generated site is checked for drift; the layer guides and architecture document are maintained by hand.

## What this means for you as a reader

Treat the manual as a well-sourced starting point, not an oracle. For any decision that carries real cost, follow the link in [section 27](../MANUAL.md#27-sources-and-verification) and read the primary source. That is why every volatile claim carries one.

The claims most worth checking yourself before committing money or architecture: model licences, because they are legal guidance by implication and change without notice; benchmark figures, because they are frequently reported for a different model variant or a different reasoning mode than the one named; and anything marked `indicative`.

## What this means for you as a contributor

A correction needs a primary source: a model card, a licence file, official documentation, or a paper. News articles, blog roundups, and social posts do not qualify, because they are themselves uncited summaries.

If you find a claim whose source does not support it, that is the most valuable issue you can open. Automation cannot find those.

## Keeping this page honest

This page describes the checks that exist today. It has been wrong before: an earlier version listed two gates when five jobs were running, and asserted it was a complete list. If you find a gap between what this page claims and what `.github/workflows/` actually runs, that gap is a defect worth reporting.
