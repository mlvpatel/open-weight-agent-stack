# Layer 8: Code agent

> Software that writes and tests software, under the same governance as everything else. Ring: harness. Manual: [section 24](../../MANUAL.md#24-code-agents-the-full-landscape).

## What this layer does

The code agent is a tool-using client of the rest of the stack: it edits files, runs tests, and opens PRs inside a sandbox, with the step budgets and write gates every other tool obeys. The full landscape with licences and rankings is [section 24](../../MANUAL.md#24-code-agents-the-full-landscape); this file carries the links.

## The options

| Tool | Class | Link |
|---|---|---|
| Cline | IDE extension, any model, permissioned | [github.com/cline/cline](https://github.com/cline/cline) |
| Kilo Code | Actively maintained Cline-lineage option, ships a JetBrains build | [github.com/Kilo-Org/kilocode](https://github.com/Kilo-Org/kilocode) |
| Aider | Terminal, git-native. Dormant since May 2026; still works, not developed | [github.com/Aider-AI/aider](https://github.com/Aider-AI/aider) |
| Continue | Read-only since 2026, no longer maintained | [github.com/continuedev/continue](https://github.com/continuedev/continue) |
| OpenHands | Autonomous, sandboxed | [github.com/OpenHands/OpenHands](https://github.com/OpenHands/OpenHands) |
| Goose | Terminal agent, extensible; now under the Linux Foundation's Agentic AI Foundation | [github.com/aaif-goose/goose](https://github.com/aaif-goose/goose) |
| Cursor | AI-first IDE | [cursor.com](https://cursor.com/) |
| Zed | Fast editor with agent panel | [zed.dev](https://zed.dev/) |
| Claude Code | Terminal and IDE agent | [claude.com/claude-code](https://claude.com/claude-code) |
| Tabnine | Self-hosted, air-gapped completion | [tabnine.com](https://www.tabnine.com/) |
| Qodo | Test generation, PR review | [qodo.ai](https://www.qodo.ai/) |

## Wiring it in

Point any of the model-agnostic entries at your own serving endpoint from layer 6 and the code agent runs fully on open weights. Agent-authored PRs record which model, prompt version, and budget produced them ([section 25](../../MANUAL.md#25-versioning-and-change-control)), and land through the same CI gate as human code ([section 13.1](../../MANUAL.md#131-the-agent-test-pyramid)).
