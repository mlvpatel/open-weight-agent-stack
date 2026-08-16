# L9: Memory and cache

> State that outlives a turn, and speed that skips one. Ring: context. Manual: [section 12](../../MANUAL.md#12-memory-and-data-tiers), [section 16](../../MANUAL.md#16-databases-and-state).

## What this layer does

Four tiers with four lifetimes: turn state dies with the turn, session state with the session, long-term memory persists until reviewed or expired, and the semantic cache turns repeated questions into instant answers. Writes pass a gate (provenance check, PII redaction) because stored text re-enters future context windows; reads are scored by relevance, recency, and importance, and labelled as memory rather than fact.

## Deployment memory decision matrix

| System | Deployment role | Required deployment review | Primary source |
|---|---|---|---|
| Hermes Agent | Bounded runtime-managed context and external providers | Profile/home isolation plus provider-specific egress and deletion; this is an agent harness, not a general store | [memory](https://hermes-agent.nousresearch.com/docs/user-guide/features/memory) · [providers](https://hermes-agent.nousresearch.com/docs/user-guide/features/memory-providers) |
| Claude-Mem | Hook-based developer-session capture, compression, and reinjection | Hook capture, model-provider egress, and telemetry must match the data policy | [repository](https://github.com/thedotmack/claude-mem) · [architecture](https://docs.claude-mem.ai/architecture/overview) · [telemetry](https://docs.claude-mem.ai/telemetry) |
| MemPalace | Local-first verbatim structured retrieval | Verbatim retention, stale content, and index maintenance; local-first applies only to the selected configuration | [repository](https://github.com/MemPalace/mempalace) |
| GBrain | Structured/provenance-aware institutional memory | Deployment version, OAuth/source isolation, and exposed MCP must be verified; taxonomy is not authorization | [repository](https://github.com/garrytan/gbrain) · [memory verbs](https://github.com/garrytan/gbrain/blob/master/docs/protocol/MEMORY_VERBS_v1.md) |
| MemSearch | Markdown source of truth plus hybrid/Milvus derived index | Canonical Markdown deletion and per-project collection separation; resetting Milvus removes only the derived index | [repository](https://github.com/zilliztech/memsearch) · [architecture](https://zilliztech.github.io/memsearch/architecture/) |
| Mem0 | Managed or self-hosted extracted-memory lifecycle | Managed versus self-hosted data paths, entity filters, and verified deletion; expiration or decay is not erasure | [repository](https://github.com/mem0ai/mem0) · [add](https://docs.mem0.ai/core-concepts/memory-operations/add) · [expiration](https://docs.mem0.ai/platform/features/memory-expiration) |

- Orchestrator-native state: LangGraph's store plus checkpointer covers turn and session tiers with no extra service.
- Semantic and embedding cache, rate limits, queues: Redis, or its open fork Valkey.
- Long-term structured memory: Postgres (with pgvector) as the system of record; Supabase when you want it hosted with auth included.
- Local-first or embedded: SQLite for state, DuckDB for analytics on traces.

## Storage and cache primitives

| Tool | Best for | Link |
|---|---|---|
| LangGraph store | State where the loop already lives | [github.com/langchain-ai/langgraph](https://github.com/langchain-ai/langgraph) |
| Redis | Semantic cache, queues, rate limits | [redis.io](https://redis.io/) |
| Valkey | Protocol-compatible open fork | [valkey.io](https://valkey.io/) |
| Postgres | System of record, pgvector co-located | [postgresql.org](https://www.postgresql.org/) |
| Supabase | Hosted Postgres with auth | [supabase.com](https://supabase.com/) |
| SQLite | Embedded state | [sqlite.org](https://www.sqlite.org/) |
| DuckDB | In-process analytics over traces | [duckdb.org](https://duckdb.org/) |

## Wiring, security, and lifecycle policy

Retrieved memory is untrusted data, never instructions. Hooks and MCP inherit tool authority; review
their credentials and reachable tools before enabling capture or reinjection. Cache keys carry the
entitlement scope and policy version, never the question alone. Writes require provenance,
corroboration, quarantine for uncertain material, and principal and tenant scoping before promotion.
PII is redacted at write time. The write-gate is also the memory-poisoning control (ASI06 in
[section 19](../../MANUAL.md#19-threat-model)).

Local-first is configuration-specific: review provider and telemetry egress for the selected storage,
MCP, hook, and managed-service configuration. Decay, expiration, and index reset are not verified
deletion. Erasure must cover canonical sources and derived indexes, caches, traces, backups, and
provider copies. Full storage-class table: [section 16](../../MANUAL.md#16-databases-and-state).
