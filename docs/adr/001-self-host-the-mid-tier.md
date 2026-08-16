# ADR 001: Self-host the mid-tier, call the frontier

- Status: accepted
- Date: 16 August 2026
- Manual: [section 22](../../MANUAL.md#22-task-to-model-routing), [section 4](../../MANUAL.md#4-the-design-method-hld-lld-and-the-rules)

## Context

Open-weight flagships crossed a terabyte of 4-bit weights. Kimi K3, DeepSeek V4 Pro, and GLM-5.2 are MIT or similarly permissive, and still too large for one node. A manual that tells a 24 GB team to "run the frontier locally" is lying. A manual that tells them to send every token to an API is leaving latency, cost, and data-residency on the table.

## Decision

Route by hosting footprint, not by brand:

- **Self-host the mid-tier** that fits one node: DeepSeek V4 Flash, gpt-oss-120b, Qwen 3.8 27B, GLM-4.5-Air on enough VRAM. This is the default for extraction, classification, structured output, and high-volume turns.
- **Call the frontier over an API** when the task is long-horizon reasoning or the weights do not fit. Kimi K3, DeepSeek V4 Pro, Qwen 3.8 Max, and the closed frontier sit here.
- **One OpenAI-compatible router** in front, so swapping an endpoint is a base-URL change.

## Options considered

| Option | Why rejected |
|---|---|
| Self-host the flagship | 4-bit K3 is well over a terabyte. A 16-24 GB row cannot serve it. |
| API for every turn | Prefill of a repeated system prompt is the cheapest large win, and it only exists if you own the server. Data-residency and per-token cost also lose. |
| One model for every task | The fast tier and the reasoning tier have different KV, batch, and latency shapes. Combining them wastes the expensive one. |

## Consequences

The architecture in sections 1-16 does not change when the endpoint changes. Eval sets must be measured per checkpoint, not per family name. GLM-4.5-Air is a fast-decode MoE, not a 9B-class guest on a 16 GB card; see section 9.

## What would reverse this

A dense open model in the 30-70B class that matches V4 Pro on the team's coding eval at batch 8 on one 48 GB GPU. Until that measurement exists, keep the split.
