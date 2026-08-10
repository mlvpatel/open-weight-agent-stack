# Layer 4: Knowledge decision

> Retrieve, or answer directly. The cheapest routing decision in the stack. Ring: context. Manual: [section 8](../../MANUAL.md#8-rag-pipeline-internals), [section 9](../../MANUAL.md#9-model-routing).

## What this layer does

Not every question deserves a retrieval round-trip. A working stack decides per request whether the model's own knowledge suffices, whether the corpus must be consulted, or whether live data through a tool is the only honest answer. Skipping this layer means paying retrieval latency on every turn and stuffing context with passages the model did not need.

## How to choose

- Start with heuristic rules: retrieve when the query names internal entities, dates after the model's cutoff, or the user's own data. Ship this first.
- Graduate to a classifier when heuristics accumulate exceptions: a fast-tier model labels each query retrieve / direct / tool in a few tokens.
- Always-retrieve is legitimate for pure document-QA products; the decision layer is then a constant.
- A router model that also picks the target model ([section 9](../../MANUAL.md#9-model-routing)) merges this with cost routing.

## The options

| Approach | Cost per decision | Link |
|---|---|---|
| Heuristic rules | Free | Pattern list in your gateway code |
| Fast-tier classifier | A few tokens | [GLM-4.5-Air](https://huggingface.co/zai-org/GLM-4.5-Air) · [Qwen3.5-9B](https://huggingface.co/Qwen/Qwen3.5-9B) |
| Semantic router | One embedding | [github.com/aurelio-labs/semantic-router](https://github.com/aurelio-labs/semantic-router) |
| Always-retrieve | One retrieval round-trip per turn | [Section 8](../../MANUAL.md#8-rag-pipeline-internals) |

## Wiring it in

The decision runs inside the orchestrator before any retrieval client is invoked, and its verdict is logged in the trace so eval can measure it: false "direct" answers show up as unsupported claims, false "retrieve" verdicts show up as latency with unused passages. Both are measurable in the eval suite ([section 13](../../MANUAL.md#13-guardrails-evals-and-the-improvement-loop)).
