# Deep Research Agent (MiniMax Edition)

A step-by-step workshop that builds a deep research agent from scratch, now powered by MiniMax M2.7. Each step introduces one idea, starting from a raw API call and ending with a planning agent that delegates to subagents.

## What's Different

This fork replaces Google Gemini with **MiniMax M2.7** via the Anthropic-compatible API endpoint, with:
- Extended thinking enabled by default
- Uses `uv` for package management
- .env file configuration (no more shell export requirements)
- Logfire + OpenTelemetry tracing preserved

## How the code progresses

The code lives in [`steps/`](steps/). Each folder is a self-contained snapshot — you can run any step on its own.

```
steps/
├── 01-minimal-call          → agent.py
├── 02-single-tool           → agent.py
├── 03-tool-runtime          → agent.py, tools.py
├── 04-run-state-and-context → agent.py, tools.py, state.py
├── 05-hooks                 → agent.py, tools.py, state.py
├── 06-creating-an-agent     → agent.py, tools.py, state.py
├── 07-subagents             → agent.py, tools.py, state.py, app.py
├── 08-beautifying-the-outputs → agent.py, tools.py, state.py, app.py
├── 09-generating-a-plan     → agent.py, tools.py, state.py, app.py
└── 10-adding-open-telemetry → agent.py, tools.py, state.py, app.py
```

1. **`01-minimal-call`** — Make the smallest possible MiniMax call with a hand-written tool schema. See what a `tool_use` block looks like. Never actually execute the tool.
2. **`02-single-tool`** — Add a real `read_file` handler, execute the call, send the result back as a `tool_result`. Full manual round-trip, but everything is hard-coded.
3. **`03-tool-runtime`** — Extract a `Tool` dataclass (name, Pydantic args model, async handler) and an `AgentRuntime` that dispatches by name. First file split: `tools.py`.
4. **`04-run-state-and-context`** — Add `state.py` with `RunConfig`, `RunState`, and `AgentContext`. Tool handlers receive `(args, state, context)`. Iteration limits and todo tracking live in the right place.
5. **`05-hooks`** — Decouple rendering from the core loop with `.on("message", ...)`, `.on("llm_tool_call", ...)`, `.on("tool_result", ...)`. Add `prepare_request()` and a user input REPL.
6. **`06-creating-an-agent`** — Rename `AgentRuntime` → `Agent`, add `run_until_idle()` that loops until the model stops calling tools. Nudge the model if `state.is_incomplete()`.
7. **`07-subagents`** — Spawn child `Agent` instances with their own config, state, and iteration budget. Dispatch search queries concurrently. Add `app.py` as the new entrypoint.
8. **`08-beautifying-the-outputs`** — Richer tool result rendering (syntax-highlighted file reads, formatted errors, bash exit codes). Runtime unchanged — all work is in hook callbacks.
9. **`09-generating-a-plan`** — Add a `mode` field (`"plan"` / `"execute"`) to `RunState`. Plan mode offers only `generate_plan`; calling it seeds todos and switches to execute mode with the full tool set.
10. **`10-adding-open-telemetry`** — Instrument the agent with Logfire and OpenTelemetry. Add a named turn span per agent run, attach the model request metadata directly to that span, and use smaller `tool_call` / `tool_executed` spans for each tool plus delegated-search subagent spans.

See [`airpods_report.md`](./airpods_report.md) for a sample output from the step 10 agent.

## Quick Start

```bash
# Clone and navigate
git clone https://github.com/Fatih0234/search-for-me-minimax.git
cd search-for-me-minimax

# Install dependencies (uses uv)
uv sync

# Configure environment
cp .env.example .env
# Edit .env with your keys:
# MINIMAX_API_KEY=your_key
# EXA_API_KEY=your_key
# LOGFIRE_API_KEY=your_token  # optional

# Run the agent
uv run python steps/10-adding-open-telemetry/app.py
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `MINIMAX_API_KEY` | Yes | Get from [platform.minimax.io](https://platform.minimax.io) |
| `EXA_API_KEY` | Yes | Get from [exa.ai](https://exa.ai) for web search |
| `LOGFIRE_API_KEY` | No | For tracing via [logfire.pydantic.dev](https://logfire.pydantic.dev) |
| `ANTHROPIC_BASE_URL` | No | Defaults to `https://api.minimax.io/anthropic` |

## Features

- **Multi-step research** with plan/execute modes
- **Web search** via Exa API with subagent parallelism
- **File operations** - read, write, edit files
- **Todo tracking** for iterative research
- **Bash command execution** for local workflows
- **Extended thinking** enabled (MiniMax M2.7)
- **Observability** with Logfire tracing

## Tech Stack

- **LLM**: MiniMax M2.7 (via Anthropic-compatible API)
- **Search**: Exa API
- **Tracing**: Logfire/OpenTelemetry
- **Package Manager**: uv
- **Python**: 3.12+

---

*Based on the original workshop by [hugobowne](https://github.com/hugobowne/build-your-own-deep-research-agent)*