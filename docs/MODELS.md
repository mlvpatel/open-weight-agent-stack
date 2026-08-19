# Open-weight model families and their licences

The families this stack draws from. **Licences are stated per model, never per family**, because most families are not internally consistent: the same organisation ships Apache-2.0, custom, and non-commercial terms side by side. A family-level claim would be legal guidance by implication, and wrong.

Every licence below is linked to a model card or vendor licence document where practical. The linked primary source wins over this page; check the exact checkpoint before you commit.

**Last verified:** 16 August 2026, against Hugging Face model-card licence tags for the named checkpoints. A tag of `other` means the card ships a named custom licence, not an OSI-approved SPDX id.

## Read this first

Three traps that have caught people, all verified against primary sources:

- **A permissive family name does not mean a permissive model.** MiniMax ships Apache-2.0, modified-MIT, and non-commercial models under one brand.
- **A quantised republish does not reliably inherit the original licence.** NVIDIA's NVFP4 checkpoints carry a mix of Apache-2.0, MIT, and NVIDIA-specific terms. Two checkpoints of the *same* base model can differ.
- **Announced is not published.** A model with benchmark scores in the press may have no downloadable weights at all.

## Linked examples with the same stated licence

These are specific checkpoints, not a licence promise for every model published by the organisation.

| Model or family | Organisation | Licence | Link |
|---|---|---|---|
| DeepSeek V4 Pro, V4 Flash | DeepSeek | MIT | [V4 Pro](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro) · [V4 Flash](https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash) |
| GLM-5.2, GLM-4.5-Air | Z.ai | MIT | [GLM-5.2](https://huggingface.co/zai-org/GLM-5.2) · [GLM-4.5-Air](https://huggingface.co/zai-org/GLM-4.5-Air) |
| gpt-oss-120b, gpt-oss-20b | OpenAI | Apache-2.0 | [gpt-oss-120b](https://huggingface.co/openai/gpt-oss-120b) · [gpt-oss-20b](https://huggingface.co/openai/gpt-oss-20b) |
| OLMo 3 | Allen Institute | Apache-2.0 (weights, data and code) | [OLMo 3 7B](https://huggingface.co/allenai/Olmo-3-1025-7B) |
| Granite 4.1 | IBM | Apache-2.0 | [Granite 4.1 30B](https://huggingface.co/ibm-granite/granite-4.1-30b) |
| Ling 3.0 | Ant Group | MIT | [Ling 3.0 Flash](https://huggingface.co/inclusionAI/Ling-3.0-flash) |
| Hunyuan Hy3 | Tencent | Apache-2.0 | [Hy3](https://huggingface.co/tencent/Hy3) |
| Phi-4, Phi-4-mini | Microsoft | MIT | [Phi-4](https://huggingface.co/microsoft/phi-4) · [Phi-4-mini](https://huggingface.co/microsoft/Phi-4-mini-instruct) |
| KAT-Coder V2.5 | Kwaipilot | Apache-2.0 | [KAT-Coder V2.5 Dev](https://huggingface.co/Kwaipilot/KAT-Coder-V2.5-Dev) |
| Kokoro-82M | hexgrad | Apache-2.0 | [hexgrad](https://huggingface.co/hexgrad/Kokoro-82M) |
| Laguna S 2.1 | poolside | OpenMDW 1.1 | [Laguna-S-2.1](https://huggingface.co/poolside/Laguna-S-2.1) |
| LFM2.5 | Liquid AI | LFM Open License v1.0 (card tag `other`, `license_name` lfm1.0) | [LFM2.5-2.6B](https://huggingface.co/LiquidAI/LFM2.5-2.6B) |
| Kimi K3 | Moonshot AI | Kimi K3 License (custom; card tag `other`, `license_name` kimi-k3) | [Kimi-K3](https://huggingface.co/moonshotai/Kimi-K3) |

## Split by model

These families ship different terms to different models. Use the specific row.

### Qwen

| Model | Licence | Note |
|---|---|---|
| Qwen3.8-27B | Apache-2.0 | Downloadable dense 27B with a vision encoder, published 14 August 2026. [Qwen3.8-27B](https://huggingface.co/Qwen/Qwen3.8-27B) |
| Qwen3.6-27B, Qwen3.5-9B | Apache-2.0 | [Qwen3.6-27B](https://huggingface.co/Qwen/Qwen3.6-27B) · [Qwen3.5-9B](https://huggingface.co/Qwen/Qwen3.5-9B) |
| Qwen3-Coder-Next | Apache-2.0 | [Model card](https://huggingface.co/Qwen/Qwen3-Coder-Next) |
| Qwen3-Embedding-8B | Apache-2.0 | [Model card](https://huggingface.co/Qwen/Qwen3-Embedding-8B) |
| Qwen 2 and 2.5, most sizes | Apache-2.0 | Includes [Qwen2.5-7B](https://huggingface.co/Qwen/Qwen2.5-7B-Instruct), [14B](https://huggingface.co/Qwen/Qwen2.5-14B-Instruct), [32B](https://huggingface.co/Qwen/Qwen2.5-32B-Instruct) and [Coder-32B](https://huggingface.co/Qwen/Qwen2.5-Coder-32B-Instruct) |
| Qwen 2.5-72B, 2.5-3B, Qwen 1.5 | Qwen License Agreement, or Tongyi Qianwen for the 1.5 line (tagged `other`) | Size decides here, not generation; see each card's licence tag |
| Qwen 3.8 Max | Custom `qwen3.8-max` (tagged `other`) | The base checkpoint [Qwen3.8-2.4T-A95B](https://huggingface.co/Qwen/Qwen3.8-2.4T-A95B) publishes first-party weights, 2.4T total / 95B active, text generation only, verified 19 August 2026. The Max API product adds vision input and built-in tools; at this scale the weights are consumed through an API in practice |

### Gemma

| Model | Licence | Note |
|---|---|---|
| Gemma 4 core series (E2B, E4B, 12B, 26B-A4B, 31B) | Apache-2.0 | The generation that moved |
| Gemma 3, 3n, 2 and earlier | Gemma Terms of Use (custom, not OSI-approved) | |
| translategemma | Gemma Terms of Use | Released 2026 and still **not** Apache-2.0 |
| medgemma | Health AI Developer Foundations terms | |
| gemma-scope | CC-BY-4.0 | |

Scope any "Gemma is Apache-2.0 now" claim to the core numbered Gemma 4 series. The sibling variants did not move.

### Mistral

| Model | Licence | Note |
|---|---|---|
| Mistral-Large-3-675B | Apache-2.0 | [Model card](https://huggingface.co/mistralai/Mistral-Large-3-675B-Instruct-2512) |
| Mistral-Small-4-119B | Apache-2.0 | [Model card](https://huggingface.co/mistralai/Mistral-Small-4-119B-2603) |
| Devstral-Small-2-24B | Apache-2.0 | [Model card](https://huggingface.co/mistralai/Devstral-Small-2-24B-Instruct-2512) |
| Mistral-Medium-3.5, Devstral-2-123B | Modified MIT with a monthly-revenue cap | A commercial-eligibility threshold, not a research restriction |
| 2024-era Large, Small, Pixtral, Ministral | Mistral Research License | Genuinely research-only |
| Codestral-22B | Mistral Non-Production License | |
| Voxtral TTS | CC-BY-NC-4.0 | Non-commercial |

### Falcon

| Model | Licence |
|---|---|
| Falcon3 series, Falcon-H1, Falcon-E | Falcon LLM License |
| falcon-mamba-7b | A separate Falcon Mamba licence document |
| Falcon-OCR | Apache-2.0 |
| falcon-7b, falcon-40b | Apache-2.0 |

### MiniMax

| Model | Licence | Note |
|---|---|---|
| MiniMax-M2.7 | **Non-commercial.** Commercial use requires prior written authorisation | The restriction lives in the repository licence file, not the card's tag. Do not plan a product around this model without contacting them |
| MiniMax-M2.5, M2.1 | MiniMax Model License (modified MIT) | |
| MiniMax-M3 | MiniMax Community License | |
| MiniMax-M1 | Apache-2.0 | |

### Llama

Licensed per generation, each with its own agreement: Llama 4 Community License, Llama 3.3, 3.2, 3.1, 3, and 2 each differ. **None is OSI-approved.** See [meta-llama](https://huggingface.co/meta-llama) and the licence file shipped with the specific model.

### BGE embeddings and rerankers

| Model | Licence |
|---|---|
| bge-m3, bge-base, bge-large | MIT |
| bge-reranker-v2-m3, v2-gemma, v2-minicpm-layerwise | Apache-2.0 |
| bge-reranker-v2.5-gemma2-lightweight | Gemma Terms of Use, not OSI-approved |

The reranker this manual recommends (`bge-reranker-v2-m3`) is Apache-2.0, not MIT. One reranker in the family inherits Gemma's custom terms.

### NVIDIA quantised checkpoints

NVFP4 republishes do **not** reliably inherit the base model's licence. Across the NVFP4 collection the tags split roughly into Apache-2.0, MIT, and NVIDIA-specific terms, and two checkpoints of the same base model can carry different tags. Some are evaluation-only.

Check the individual checkpoint every time: [nvidia](https://huggingface.co/nvidia).

## Using this page

Which model for which task: [MANUAL.md section 22](../MANUAL.md#22-task-to-model-routing). What your hardware can hold: [section 2](../MANUAL.md#2-what-can-you-actually-run). Every specific claim's source: [section 27](../MANUAL.md#27-sources-and-verification). What automated checks do and do not prove: [VERIFICATION.md](VERIFICATION.md).
