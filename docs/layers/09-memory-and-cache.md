# Layer 9: Memory and cache

> State that outlives a turn, and speed that skips one. Ring: context. Manual: [section 12](../../MANUAL.md#12-memory-and-data-tiers), [section 16](../../MANUAL.md#16-databases-and-state).

## What this layer does

Four tiers with four lifetimes: turn state dies with the turn, session state with the session, long-term memory persists until reviewed or expired, and the semantic cache turns repeated questions into instant answers. Writes pass a gate (provenance check, PII redaction) because stored text re-enters future context windows; reads are scored by relevance, recency, and importance, and labelled as memory rather than fact.

## How to choose

- Orchestrator-native state: LangGraph's store plus checkpointer covers turn and session tiers with no extra service.
- Semantic and embedding cache, rate limits, queues: Redis, or its open fork Valkey.
- Managed memory with extraction built in: Mem0.
- Long-term structured memory: Postgres (with pgvector) as the system of record; Supabase when you want it hosted with auth included.
- Local-first or embedded: SQLite for state, DuckDB for analytics on traces.

## The options

| Tool | Best for | Link |
|---|---|---|
| LangGraph store | State where the loop already lives | [github.com/langchain-ai/langgraph](https://github.com/langchain-ai/langgraph) |
| Redis | Semantic cache, queues, rate limits | [redis.io](https://redis.io/) |
| Valkey | Protocol-compatible open fork | [valkey.io](https://valkey.io/) |
| Mem0 | Extracted long-term memory | [github.com/mem0ai/mem0](https://github.com/mem0ai/mem0) |
| Postgres | System of record, pgvector co-located | [postgresql.org](https://www.postgresql.org/) |
| Supabase | Hosted Postgres with auth | [supabase.com](https://supabase.com/) |
| SQLite | Embedded state | [sqlite.org](https://www.sqlite.org/) |
| DuckDB | In-process analytics over traces | [duckdb.org](https://duckdb.org/) |

## Wiring it in

Cache keys carry the entitlement scope and policy version, never the question alone, or one tenant's cached answer leaks to another. Every tier has a TTL; PII is redacted at write time. The write-gate is also the memory-poisoning control (ASI06 in [section 19](../../MANUAL.md#19-threat-model)). Full storage-class table: [section 16](../../MANUAL.md#16-databases-and-state).
