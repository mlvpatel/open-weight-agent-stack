# L3: Orchestrator

> Plans, routes, loops, checkpoints. The container where agent behaviour lives. Ring: loop. Manual: [section 7](../../MANUAL.md#7-agent-control-loop), [section 9](../../MANUAL.md#9-model-routing).

## What this layer does

The orchestrator turns a goal into bounded work: decompose, act, observe, verify, and stop. Stopping is the hard part. Step budgets, token budgets, time budgets, and rework limits are enforced here, not requested politely in the prompt. State checkpoints after every step so a crash resumes instead of restarting.

## How to choose

- Graph-of-steps control with checkpointing: LangGraph, the current default for production loops.
- Role-based multi-agent teams: CrewAI reads naturally when work maps to roles.
- Document-heavy agents: LlamaIndex Workflows sit closest to retrieval.
- Type-safe, minimal, Pythonic: Pydantic AI validates every boundary.
- Microsoft ecosystem: Microsoft Agent Framework (successor to AutoGen and Semantic Kernel).
- Long-running, durable jobs: Temporal underneath any of the above.
- Learning or a tight scope: a plain tool loop in ~100 lines teaches more than any framework.

## The options

| Tool | Best for | Link |
|---|---|---|
| LangGraph | Stateful graphs, checkpoints, human-in-the-loop | [github.com/langchain-ai/langgraph](https://github.com/langchain-ai/langgraph) |
| CrewAI | Role-based crews | [github.com/crewAIInc/crewAI](https://github.com/crewAIInc/crewAI) |
| LlamaIndex | Retrieval-centric workflows | [github.com/run-llama/llama_index](https://github.com/run-llama/llama_index) |
| Pydantic AI | Typed agents, schema-validated boundaries | [github.com/pydantic/pydantic-ai](https://github.com/pydantic/pydantic-ai) |
| Microsoft Agent Framework | .NET and Python, enterprise integration | [github.com/microsoft/agent-framework](https://github.com/microsoft/agent-framework) |
| AWS Strands | Model-driven agents on AWS | [github.com/strands-agents/sdk-python](https://github.com/strands-agents/sdk-python) |
| smolagents | Minimal code-first agents | [github.com/huggingface/smolagents](https://github.com/huggingface/smolagents) |
| Temporal | Durable execution under any framework | [github.com/temporalio/temporal](https://github.com/temporalio/temporal) |

## Wiring it in

The orchestrator owns model routing ([section 9](../../MANUAL.md#9-model-routing)): fast tier for extraction and classification, general tier for tool loops, specialist tier for hard reasoning, each with its own thinking budget. It labels every tool result untrusted before it re-enters context, and it writes memory only through the write-gate ([section 12](../../MANUAL.md#12-memory-and-data-tiers)). Component-level view: [docs/ARCHITECTURE.md, level 3](../ARCHITECTURE.md#level-3-components).
