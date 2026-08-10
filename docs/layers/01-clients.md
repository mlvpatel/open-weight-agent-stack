# Layer 1: Clients

> Every path a request takes into the stack. Ring: harness. Manual: [section 5](../../MANUAL.md#5-master-architecture), [section 6](../../MANUAL.md#6-request-lifecycle).

## What this layer does

Web, mobile, CLI, chat platforms, scheduled jobs, and raw API calls all terminate at the same gateway and receive the same treatment: authenticate, rate-limit, validate, guard. A client is anything that can present a token; the stack does not care whether a human or a cron job is behind it.

## How to choose

You do not choose one; you decide which to support first. The practical order for most teams: web chat first (fastest feedback), API second (unlocks integrations and testing), then chat platforms (Slack or Teams, where work already happens), then scheduled agents (cron and webhooks) once budgets and guards have proven themselves, because unattended runs remove the human from the loop.

## The options

| Entry point | What it needs from the stack | Reference |
|---|---|---|
| Web and mobile apps | Streaming responses (SSE is the default transport) | [Server-sent events, MDN](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events) |
| CLI and SDKs | Stable versioned API, machine-readable errors | [Section 17](../../MANUAL.md#17-serving-budgets-and-rollback) error contract |
| Slack / Teams bots | Webhook signature verification, fast acks, async replies | [Slack API](https://api.slack.com/) |
| Cron and webhooks | Idempotency keys, dead-letter queue, spend caps per job | [Section 16](../../MANUAL.md#16-databases-and-state) queues |
| Raw API consumers | The same OpenAI-compatible surface the stack uses internally | [Section 22.1](../../MANUAL.md#221-the-api-layer-every-way-to-call-a-model) |

## Wiring it in

Two rules keep this layer boring. Every client speaks to the gateway, never directly to the model server or the vector store. And unattended clients (cron, webhooks) get the tightest budgets in the fleet, because nobody is watching them fail.
