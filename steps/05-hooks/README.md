# 05 - Hooks

This step introduces a small hook lifecycle on top of the runtime from step 04.

It shows:

- `prepare_request()`
- `on_message`
- `on_llm_tool_call`
- `on_tool_result`

The goal is to keep the runtime readable while making it easy to layer in behavior step by step.

In this step:

- `prepare_request()` builds the exact `config`, `contents`, and `tools` for inference
- an `on_message` hook renders assistant text
- an `on_llm_tool_call` hook renders tool calls
- an `on_tool_result` hook renders tool results

The main cleanup in this step is that request preparation is a normal method, while actual rendering/observation points stay as hooks.

Run it with:

```bash
uv run python3 steps/05-hooks/agent.py
```
