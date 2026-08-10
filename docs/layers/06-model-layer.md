# Layer 6: Model layer

> The serving runtime and the models it runs. Ring: prompt. Manual: [section 2](../../MANUAL.md#2-what-can-you-actually-run), [section 20](../../MANUAL.md#20-latency-budget), [section 22](../../MANUAL.md#22-task-to-model-routing).

## What this layer does

Turns weights into tokens per second. The runtime choice is hardware-shaped (see the full matrix in [section 2](../../MANUAL.md#2-what-can-you-actually-run)); the model choice is task-shaped ([section 22](../../MANUAL.md#22-task-to-model-routing)). The sizing rule that answers most questions: at 4-bit, weights need roughly 0.5 to 0.6 GB per billion parameters, before KV cache.

## How to choose

- Serving a team on NVIDIA: SGLang or vLLM; continuous batching and prefix caching are the point.
- Maximum single-GPU throughput on new NVIDIA hardware: TensorRT-LLM.
- One developer, any machine: Ollama for convenience, llama.cpp for control, LM Studio for a GUI.
- Apple Silicon: MLX, with pre-converted checkpoints from mlx-community.
- Quant format decides the runtime: GGUF for the llama.cpp family, AWQ/GPTQ/FP8 for the GPU servers ([section 2](../../MANUAL.md#2-what-can-you-actually-run)).

## The options

| Tool | Best for | Link |
|---|---|---|
| SGLang | Agent workloads, RadixAttention prefix reuse | [github.com/sgl-project/sglang](https://github.com/sgl-project/sglang) |
| vLLM | The serving default, PagedAttention | [github.com/vllm-project/vllm](https://github.com/vllm-project/vllm) |
| TensorRT-LLM | Peak NVIDIA throughput, FP8/FP4 | [github.com/NVIDIA/TensorRT-LLM](https://github.com/NVIDIA/TensorRT-LLM) |
| Ollama | One-command local serving | [github.com/ollama/ollama](https://github.com/ollama/ollama) |
| llama.cpp | CPU, Metal, Vulkan, CUDA via GGUF | [github.com/ggml-org/llama.cpp](https://github.com/ggml-org/llama.cpp) |
| MLX | Apple Silicon | [github.com/ml-explore/mlx](https://github.com/ml-explore/mlx) |
| LM Studio | Desktop GUI over MLX and llama.cpp | [lmstudio.ai](https://lmstudio.ai/) |
| gpt-oss 120b / 20b | OpenAI's Apache-2.0 MoE pair; the 120b runs on one 80 GB GPU | [Model card](https://huggingface.co/openai/gpt-oss-120b) |
| More open families | OLMo 3 · Granite 4.1 · Ling 3.0 · Hunyuan · MiniMax · Falcon · LFM edge | [Section 27](../../MANUAL.md#27-sources-and-verification) |
| Open coding models | Qwen3-Coder-Next · KAT-Coder · Devstral · Laguna | [Qwen3-Coder-Next](https://huggingface.co/Qwen/Qwen3-Coder-Next) |
| NVFP4 checkpoints | NVIDIA's prequantised open flagships for Blackwell | [huggingface.co/nvidia](https://huggingface.co/nvidia) |
| Model cards | Every model fact, first-hand | [Section 27](../../MANUAL.md#27-sources-and-verification) |

## Wiring it in

Expose everything behind one OpenAI-compatible endpoint so the orchestrator never knows which runtime answered. Warm up at boot, enable prefix caching, and watch KV pressure as the scaling signal ([section 14](../../MANUAL.md#14-deployment-topology)). PagedAttention and speculative decoding mechanics: [section 20](../../MANUAL.md#20-latency-budget).
