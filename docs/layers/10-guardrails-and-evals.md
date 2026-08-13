# Layer 10: Guardrails and evals

> Inline checks on every request; offline verdicts before every release. Ring: eval. Manual: [section 13](../../MANUAL.md#13-guardrails-evals-and-the-improvement-loop).

## What this layer does

Guards run in milliseconds on every request: schema enforcement, injection screening, PII redaction, toxicity, citation coverage. Evals run offline against a golden dataset and gate deployment; a prompt edit that drops the score does not ship. Production traces feed new cases back into the dataset, which is what makes the loop improve rather than drift. The full test pyramid, from mocked unit tests to chaos drills: [section 13.1](../../MANUAL.md#131-the-agent-test-pyramid).

## How to choose

- Structured output that cannot be malformed: Outlines (constrained decoding) beats retry loops.
- Assembled validator pipelines: Guardrails AI or NeMo Guardrails.
- A safety classifier in front of and behind the model: Llama Guard.
- RAG quality metrics: Ragas. General eval harness and CI gate: Promptfoo or DeepEval.

## The options

| Tool | Best for | Link |
|---|---|---|
| Outlines | Constrained decoding to a schema | [github.com/dottxt-ai/outlines](https://github.com/dottxt-ai/outlines) |
| Guardrails AI | Validator pipelines | [github.com/guardrails-ai/guardrails](https://github.com/guardrails-ai/guardrails) |
| NeMo Guardrails | Dialogue rails, NVIDIA ecosystem | [github.com/NVIDIA/NeMo-Guardrails](https://github.com/NVIDIA/NeMo-Guardrails) |
| Llama Guard | Input/output safety classification | [huggingface.co/meta-llama](https://huggingface.co/meta-llama) |
| Ragas | RAG-specific metrics | [github.com/explodinggradients/ragas](https://github.com/explodinggradients/ragas) |
| Promptfoo | Eval as CI gate | [github.com/promptfoo/promptfoo](https://github.com/promptfoo/promptfoo) |
| DeepEval | Pytest-style LLM tests | [github.com/confident-ai/deepeval](https://github.com/confident-ai/deepeval) |

## Wiring it in

Measure over-refusal next to correct-refusal, or hardening quietly costs usefulness. Calibrate the LLM judge against human labels before trusting it; judged metrics take the median of three runs. Red-team suites map one-to-one to the ASI risks in [section 19](../../MANUAL.md#19-threat-model) and block release on failure when your release policy requires it.
