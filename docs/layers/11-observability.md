# Layer 11: Observability

> If you cannot see the turn, you cannot debug, bill, or improve it. Ring: eval. Manual: [section 17](../../MANUAL.md#17-serving-budgets-and-rollback), [section 20](../../MANUAL.md#20-latency-budget).

## What this layer does

Every turn emits a trace: each model call with prompt version, tokens, latency and cost, every tool invocation, every guard verdict. Traces answer "why was this answer wrong" a week later; metrics feed the SLO alerts; both feed the eval dataset. PII is stripped at the sink so observability does not become a second copy of user data.

## How to choose

- LLM-native tracing with cost and quality views: Langfuse (self-hostable) or Phoenix.
- Wire format: OpenTelemetry everywhere, so nothing is locked in.
- Metrics and alerting: Prometheus scrapes, Alertmanager routes, Grafana displays; alert on error-budget burn rate, not on dashboards.
- Gateway-level usage and cost accounting: Helicone. Hosted eval-plus-observability platforms: W&B Weave, Braintrust.

## The options

| Tool | Best for | Link |
|---|---|---|
| Langfuse | LLM traces, self-hosted | [github.com/langfuse/langfuse](https://github.com/langfuse/langfuse) |
| Phoenix | Traces and evals, OTel-native | [github.com/Arize-ai/phoenix](https://github.com/Arize-ai/phoenix) |
| OpenTelemetry | The wire format | [opentelemetry.io](https://opentelemetry.io/) |
| Prometheus | Metrics and SLO math | [prometheus.io](https://prometheus.io/) |
| Grafana + Loki | Dashboards and logs | [grafana.com](https://grafana.com/) |
| Helicone | Usage and cost at the gateway | [helicone.ai](https://www.helicone.ai/) |
| W&B Weave | Hosted tracing and evals | [wandb.ai](https://wandb.ai/) |
| Braintrust | Hosted eval platform | [braintrust.dev](https://www.braintrust.dev/) |

## Wiring it in

Instrument at the gateway and orchestrator, not inside every component; propagate one trace ID end to end. The four SLO numbers that matter: time to first token, tokens per second, availability, and spend per tenant ([section 17](../../MANUAL.md#17-serving-budgets-and-rollback)). The latency budget in [section 20](../../MANUAL.md#20-latency-budget) tells you which stage to blame.
