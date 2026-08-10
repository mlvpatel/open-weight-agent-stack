# Layer 12: Deployment

> Wherever you can run it: a laptop, one GPU box, a cluster, or rented capacity. Ring: loop. Manual: [section 14](../../MANUAL.md#14-deployment-topology), [section 17](../../MANUAL.md#17-serving-budgets-and-rollback), [section 26](../../MANUAL.md#26-build-order-and-troubleshooting).

## What this layer does

The same architecture deploys at every size; only the box count changes. One machine with docker compose runs the whole stack for a team. Multi-GPU and multi-node serving add tensor parallelism and prefill/decode separation. Kubernetes enters at multi-node scale, not before. Every topology keeps the same rollback rule: prompt, model, index and config version together and roll back together.

## How to choose

- Laptop or single box: docker compose; restart-on-boot is your availability story.
- Single GPU server for a team: compose plus a reverse proxy; blue-green by running two model-server containers.
- Multi-GPU node: tensor parallelism via the serving runtime; NVLink matters more than GPU count.
- Multi-node: vLLM over Ray; Kubernetes for orchestration; autoscale on queue depth and KV pressure, never CPU.
- No hardware: rented GPUs (RunPod and peers) or serverless (Modal); managed endpoints when serving is not your business.

## The options

| Tool | Best for | Link |
|---|---|---|
| Docker / Compose | Everything below cluster scale | [docker.com](https://www.docker.com/) |
| Kubernetes | Multi-node orchestration | [kubernetes.io](https://kubernetes.io/) |
| Ray | Multi-node serving substrate | [github.com/ray-project/ray](https://github.com/ray-project/ray) |
| WSL2 | The full Linux serving stack on Windows | [learn.microsoft.com/windows/wsl](https://learn.microsoft.com/windows/wsl/) |
| Modal | Serverless GPU compute | [modal.com](https://modal.com/) |
| RunPod | Rented GPUs by the hour | [runpod.io](https://www.runpod.io/) |
| NVIDIA NIM | Prebuilt optimised containers; hosted API to try, download to self-host | [build.nvidia.com](https://build.nvidia.com/models) |
| DGX Spark | GB10, 128 GB unified memory; 70B-class on a desktop | [nvidia.com](https://www.nvidia.com/en-us/products/workstations/dgx-spark/) |
| Jetson | Orin and Thor modules; agents at the edge | [developer.nvidia.com](https://developer.nvidia.com/embedded/jetson-modules) |
| Managed K8s + accelerators | EKS + Trainium/Inferentia · GKE + TPU · AKS + ND GPUs | [TPU](https://cloud.google.com/tpu) · [Trainium](https://aws.amazon.com/ai/machine-learning/trainium/) |
| Cloud platforms | Bedrock, Vertex, Foundry and peers | [Section 23.5](../../MANUAL.md#235-where-it-runs-in-the-cloud) |

## Wiring it in

Operate to written targets from day one: SLOs on time to first token, tokens per second and availability; a one-page runbook for the four common failures; RTO and RPO decided before the incident ([section 17](../../MANUAL.md#17-serving-budgets-and-rollback)). When something breaks in the first hour, start at the symptom table in [section 26.1](../../MANUAL.md#261-when-it-breaks-the-first-hour-table).
