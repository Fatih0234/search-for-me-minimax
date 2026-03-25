# Build Your Own Deep Research Agent

A step-by-step workshop that builds a deep research agent from scratch. Each step introduces one idea, starting from a raw API call and ending with a planning agent that delegates to subagents.

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
└── 09-generating-a-plan     → agent.py, tools.py, state.py, app.py
```

1. **`01-minimal-call`** — Make the smallest possible Gemini call with a hand-written tool schema. See what a `FunctionCall` looks like. Never actually execute the tool.
2. **`02-single-tool`** — Add a real `read_file` handler, execute the call, send the result back as a `FunctionResponse`. Full manual round-trip, but everything is hard-coded.
3. **`03-tool-runtime`** — Extract a `Tool` dataclass (name, Pydantic args model, async handler) and an `AgentRuntime` that dispatches by name. First file split: `tools.py`.
4. **`04-run-state-and-context`** — Add `state.py` with `RunConfig`, `RunState`, and `AgentContext`. Tool handlers receive `(args, state, context)`. Iteration limits and todo tracking live in the right place.
5. **`05-hooks`** — Decouple rendering from the core loop with `.on("message", ...)`, `.on("llm_tool_call", ...)`, `.on("tool_result", ...)`. Add `prepare_request()` and a user input REPL.
6. **`06-creating-an-agent`** — Rename `AgentRuntime` → `Agent`, add `run_until_idle()` that loops until the model stops calling tools. Nudge the model if `state.is_incomplete()`.
7. **`07-subagents`** — Spawn child `Agent` instances with their own config, state, and iteration budget. Dispatch search queries concurrently. Add `app.py` as the new entrypoint.
8. **`08-beautifying-the-outputs`** — Richer tool result rendering (syntax-highlighted file reads, formatted errors, bash exit codes). Runtime unchanged — all work is in hook callbacks.
9. **`09-generating-a-plan`** — Add a `mode` field (`"plan"` / `"execute"`) to `RunState`. Plan mode offers only `generate_plan`; calling it seeds todos and switches to execute mode with the full tool set.

See [`report.md`](report.md) for a sample output from the step 09 agent.

## Running a step

```bash
cd steps/09-generating-a-plan
python app.py  # or agent.py for earlier steps
```

Requires a `GEMINI_API_KEY` environment variable. Later steps also use `EXA_API_KEY` for web search.
