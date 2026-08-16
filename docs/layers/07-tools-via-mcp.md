# L7: Tools via MCP

> The agent's hands, behind contracts and sandboxes. Ring: harness. Manual: [section 11](../../MANUAL.md#11-trust-boundaries), [section 19](../../MANUAL.md#19-threat-model).

## What this layer does

Tools are how the agent touches the world: repositories, chat, tickets, databases, filesystems, the web. MCP standardises the interface so one server serves every MCP-speaking client. Two properties are non-negotiable: every tool call is schema-validated before execution, and every tool result re-enters context labelled untrusted, because a fetched web page or issue body is attacker-controllable text.

## How to choose

- Reach an external system an MCP server already exists for: use it, pinned by version.
- Internal API: wrap it with a thin MCP server or expose an OpenAPI spec as tools.
- Tools that execute model-written code: sandbox is mandatory; container at minimum, gVisor or Firecracker for stronger isolation, E2B or Modal hosted.
- Agent-to-agent across vendors: A2A, not bespoke glue.

## The options

| Tool | Best for | Link |
|---|---|---|
| MCP specification | The protocol | [modelcontextprotocol.io](https://modelcontextprotocol.io/) |
| Reference MCP servers | Filesystem, GitHub, and more, maintained upstream | [github.com/modelcontextprotocol/servers](https://github.com/modelcontextprotocol/servers) |
| OpenAPI tools | Existing REST APIs as tools | Your API's spec |
| E2B | Hosted code sandboxes | [e2b.dev](https://e2b.dev/) |
| Modal | Sandboxes plus serverless compute | [modal.com](https://modal.com/) |
| gVisor | Syscall-filtering container sandbox | [gvisor.dev](https://gvisor.dev/) |
| Firecracker | MicroVM per execution | [firecracker-microvm.github.io](https://firecracker-microvm.github.io/) |
| A2A | Agent-to-agent interop | [a2a-protocol.org](https://a2a-protocol.org/latest/) |

## Wiring it in

Pin MCP servers by version and review their tool lists in PRs; the supply chain row ASI04 in [section 19](../../MANUAL.md#19-threat-model) is about exactly this. Writes go through idempotency keys, spend caps, and, above a risk threshold, human approval. Credentials live in the harness, never in the prompt.
