# Layer 2: Frontend and edge

> Capture the prompt, stream the answer, never blank the page. Ring: harness. Manual: [section 6](../../MANUAL.md#6-request-lifecycle).

## What this layer does

The frontend's whole job is honesty about latency: show the first token the moment it exists, render citations as they arrive, and keep the page readable if scripts fail. Time to first token is the number users feel; this layer is where it becomes visible.

## How to choose

- Product UI for real users: Next.js or SvelteKit with SSE streaming.
- Internal tools and demos in Python: Streamlit or Gradio, hours to ship.
- Chat-specific UI without building one: Open WebUI self-hosted, or Chainlit embedded in a Python app.
- React chat components inside an existing app: assistant-ui or CopilotKit drop in.

## The options

| Tool | Best for | Link |
|---|---|---|
| Next.js | Production web apps, streaming SSR | [nextjs.org](https://nextjs.org/) |
| SvelteKit | Lighter production alternative | [svelte.dev](https://svelte.dev/) |
| Vercel AI SDK | Streaming hooks and tool-call rendering in TS | [github.com/vercel/ai](https://github.com/vercel/ai) |
| Streamlit | Python internal tools | [streamlit.io](https://streamlit.io/) |
| Gradio | Python demos, HF-native | [gradio.app](https://www.gradio.app/) |
| Chainlit | Chat UI for Python agent apps | [chainlit.io](https://chainlit.io/) |
| Open WebUI | Self-hosted chat front end for any OpenAI-compatible server | [github.com/open-webui/open-webui](https://github.com/open-webui/open-webui) |
| assistant-ui | React chat primitives | [github.com/assistant-ui/assistant-ui](https://github.com/assistant-ui/assistant-ui) |
| CopilotKit | Embedded copilot UI in React apps | [github.com/CopilotKit/CopilotKit](https://github.com/CopilotKit/CopilotKit) |

## Wiring it in

Stream over SSE from the gateway; buffer nothing you could show. Render content visible by default and treat motion as an enhancement, so a script failure degrades to a readable page instead of a blank one. Handle the retract-and-replace case: if the final output guard fails after streaming, the UI must be able to replace shown text with the repaired answer ([section 13](../../MANUAL.md#13-guardrails-evals-and-the-improvement-loop)).
