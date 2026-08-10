# Open-weight model families and their licences

The families this stack draws from. **Licences are stated per model, never per family**, because most families are not internally consistent: the same organisation ships Apache-2.0, custom, and non-commercial terms side by side. A family-level claim would be legal guidance by implication, and wrong.

Every licence below was read from the model card's own licence tag or the vendor's licence document. The model card always wins over this page. Check it before you commit.

## Read this first

Three traps that have caught people, all verified against primary sources:

- **A permissive family name does not mean a permissive model.** MiniMax ships Apache-2.0, modified-MIT, and non-commercial models under one brand.
- **A quantised republish does not reliably inherit the original licence.** NVIDIA's NVFP4 checkpoints carry a mix of Apache-2.0, MIT, and NVIDIA-specific terms. Two checkpoints of the *same* base model can differ.
- **Announced is not published.** A model with benchmark scores in the press may have no downloadable weights at all.

## Uniformly licensed

Safe to state at family level, because every current member agrees.

| Model or family | Organisation | Licence | Link |
|---|---|---|---|
| DeepSeek V4 Pro, V4 Flash | DeepSeek | MIT | [deepseek-ai](https://huggingface.co/deepseek-ai) |
| GLM-5.2, GLM-4.5-Air | Z.ai | MIT | [zai-org](https://huggingface.co/zai-org) |
| gpt-oss-120b, gpt-oss-20b | OpenAI | Apache-2.0 | [openai](https://huggingface.co/openai) |
| OLMo 3 | Allen Institute | Apache-2.0 (weights, data and code) | [allenai](https://huggingface.co/allenai) |
| Granite 4.1 | IBM | Apache-2.0 | [ibm-granite](https://huggingface.co/ibm-granite) |
| Ling 3.0 | Ant Group | MIT | [inclusionAI](https://huggingface.co/inclusionAI) |
| Hunyuan Hy3 | Tencent | Apache-2.0 | [tencent](https://huggingface.co/tencent) |
| Phi-4, Phi-4-mini | Microsoft | MIT | [microsoft](https://huggingface.co/microsoft) |
| KAT-Coder V2.5 | Kwaipilot | Apache-2.0 | [Kwaipilot](https://huggingface.co/Kwaipilot) |
| Kokoro-82M | hexgrad | Apache-2.0 | [hexgrad](https://huggingface.co/hexgrad/Kokoro-82M) |
| Laguna S 2.1 | poolside | OpenMDW 1.1 | [poolside](https://huggingface.co/poolside) |
| LFM2.5 | Liquid AI | LFM Open License v1.0 | [LiquidAI](https://huggingface.co/LiquidAI) |
| Kimi K3 | Moonshot AI | Kimi K3 License (custom) | [moonshotai](https://huggingface.co/moonshotai) |

## Split by model

These families ship different terms to different models. Use the specific row.

### Qwen

| Model | Licence | Note |
|---|---|---|
| Qwen3.6-27B, Qwen3.5-9B | Apache-2.0 | The self-host tier |
| Qwen3-Coder-Next | Apache-2.0 | Coding specialist |
| Qwen3-Embedding-8B | Apache-2.0 | Embeddings |
| Qwen 2 and 2.5, most sizes | Apache-2.0 | Includes Qwen2.5-7B, 14B, 32B and Qwen2.5-Coder-32B |
| Qwen 2.5-72B, 2.5-3B, Qwen 1.5 | Qwen License Agreement, or Tongyi Qianwen for the 1.5 line (tagged `other`) | Size decides here, not generation |
| Qwen 3.8 Max | **No published weights** | Announced with benchmark figures; no downloadable checkpoint under the Qwen organisation. Treat as an API model, not an open-weight one. Third-party uploads claiming to be it are not authoritative |

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
| Mistral-Large-3-675B | Apache-2.0 | The flagship **is** permissive |
| Mistral-Small-4-119B | Apache-2.0 | |
| Devstral-Small-2-24B | Apache-2.0 | The open coding model |
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
