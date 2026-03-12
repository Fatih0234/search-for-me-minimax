# Build Your Own Deep Research Agent

Small workshop examples for building a deep research agent with the Gemini Interactions API.

## Setup

Install dependencies:

```bash
uv sync
```

Environment variables:

- `GOOGLE_API_KEY` — required for all workshops
- `EXA_API_KEY` — required for workshops 3 and 4 (web search via Exa)

## Testing

Scripts are progressive within each workshop — start from the top and work down. Each script runs standalone with hardcoded mock data (no need to run earlier workshops first), except `end_to_end.py` which is interactive.

```bash
# Workshop 1 — Generating our Research Plan
uv run python3 "workshops/1 - Generating our Research Plan/response.py"
uv run python3 "workshops/1 - Generating our Research Plan/tools.py"
uv run python3 "workshops/1 - Generating our Research Plan/questions.py"          # interactive
uv run python3 "workshops/1 - Generating our Research Plan/questions_with_plan.py" # interactive

# Workshop 2 — Migrating to Textual
uv run python3 "workshops/2 - migrating to Textual/shell.py"

# Workshop 3 — Running sub-agents
uv run python3 "workshops/3 - Running sub-agents/search.py"    # Exa only — check your API key works
uv run python3 "workshops/3 - Running sub-agents/subagent.py"  # single sub-agent (Gemini + Exa)
uv run python3 "workshops/3 - Running sub-agents/fan_out.py"   # 3 sub-agents in parallel

# Workshop 4 — Synthesizing the report
uv run python3 "workshops/4 - Synthesizing the report/synthesize.py"   # Gemini only, uses mock results
uv run python3 "workshops/4 - Synthesizing the report/end_to_end.py"   # full interactive pipeline
```

## 1 - Generating our Research Plan

This section is about turning a vague research idea into a scoped research plan.

Rough shape:

- `response.py`: the smallest possible Interactions API example
- `tools.py`: a single tool-calling example with `clarifyScope`
- `questions.py`: a clarification loop that gathers missing information and outputs a research brief
- `questions_with_plan.py`: takes that research brief and turns it into a user-facing response plus a todo list

## 2 - migrating to Textual

This section is about moving the agent UI to Textual.

Rough shape:

- a persistent input box at the bottom of the screen
- a transcript area above it
- a reusable shell foundation for wiring in the queue and agent runtime

Archived:

- `workshops/archive/2 - Creating our minimal agent`: the plain terminal prototype with the in-memory steer / queue behavior

## 3 - Running sub-agents

This section fans out research to parallel sub-agents, each using Exa web search as a Gemini tool.

Requires `EXA_API_KEY` environment variable (in addition to `GOOGLE_API_KEY`).

Rough shape:

- `search.py`: the smallest possible Exa search call — proof the dependency works
- `subagent.py`: a single sub-agent that takes a todo item, searches the web via tool calls, and returns a markdown summary
- `fan_out.py`: runs multiple sub-agents in parallel using `ThreadPoolExecutor` and collects results

## 4 - Synthesizing the report

This section takes sub-agent results and produces a final cohesive research report.

Rough shape:

- `synthesize.py`: takes the original request + sub-agent results and asks Gemini to produce a structured markdown report
- `end_to_end.py`: wires the full pipeline together — clarification → plan → sub-agents → report

## Notes

- These scripts use the experimental Gemini Interactions API via `google-genai`.
- Rich is used for terminal formatting, including markdown rendering.
- The examples are intentionally simple and optimized for workshop/demo use rather than production robustness.
