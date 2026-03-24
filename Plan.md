# Cleaner Hook-Based Agent Plan

## Goals

- Keep the workshop's hook-based teaching story.
- Make the runtime read like a clear workflow instead of a mini framework.
- Reduce duplicated runtime/tool code across workshop variants.
- Keep rendering flexible via `shell.write(...)` while still supporting updatable live blocks.
- Remove overly defensive patterns like `call.args or {}` and validate tool inputs at the boundary.

## Design Principles

- Keep the core loop explicit.
- Use hooks for lifecycle extension and rendering.
- Keep config, mutable run state, and dependencies separate.
- Prefer plain functions plus typed models over deep class hierarchies.
- Validate inputs early and fail loudly instead of quietly compensating for bad state.

## Proposed Core Types

### `RunConfig`

Static configuration for a run.

- `model`
- `max_iterations`
- any future run-level settings like subagent iteration budgets

This should be immutable for the duration of a run.

### `RunState`

Mutable workflow state for the current run.

- `iteration_count`
- `mode`
- `todos`

This should also expose a small API for state transitions:

- `add_todos(...)`
- `remove_todos(...)`

Do not store config like `max_iterations` here.

### `AgentContext`

Long-lived dependencies only.

- `shell`
- `exa`
- `db`
- other service clients as needed

This is a plain dependency container. It should not become a service locator with `require_*` helpers.

### `Tool`

Each tool should be defined by:

- `name`
- `description`
- `args_model`
- `handler`

The handler should be a plain async function:

```python
async def handler(args: ArgsModel, state: RunState, context: AgentContext) -> dict[str, Any]:
    ...
```

This is simpler than subclass-based tools while still keeping typed inputs.

## Runtime Shape

The agent loop should stay explicit and top-to-bottom:

1. Increment iteration count.
2. Run `before_model` hooks.
3. Call the model.
4. Run `after_model` hooks.
5. Extract tool calls.
6. Validate and execute tool calls.
7. Run `after_tools` hooks.
8. Stop or continue based on explicit agent logic.

The runtime should not hide core behavior behind too many generic abstractions.

## Hooks

Keep the hook model, but keep it small.

Recommended hook points:

- `before_model`
- `after_model`
- `after_tools`

These are enough for the workshop.

### What Hooks Should Do

- inject prompt context such as current todos or mode reminders
- render assistant/tool output
- perform small lifecycle-specific state adjustments

### What Hooks Should Not Do

- become the only place core control flow lives
- hide important state transitions across many files
- silently compensate for malformed runtime inputs

The agent should still be readable without searching the entire codebase for hook registrations.

## Rendering

Keep rendering hook-based and centered on a generic `shell.write(...)`.

That matches the workshop well and keeps rendering flexible for:

- markdown
- panels
- syntax blocks
- custom widgets
- live-updating blocks

On top of `write(...)`, add one lightweight concept for persistent updateable UI:

- `create_block(...) -> BlockHandle`

Where `BlockHandle` supports:

- `update(...)`
- `remove()`

Use this for:

- status display
- subagent live output
- long-running tool progress

Do not introduce a reducer or a large render-event hierarchy unless the code later proves it is necessary.

## Tool Validation Rule

This is the main runtime rule:

- Validate tool call arguments once at the execution boundary.
- If arguments are missing or malformed, raise an error immediately.
- Do not paper over invalid calls with fallback patterns like `call.args or {}`.

Bad:

```python
args = tool.args_model.model_validate(call.args or {})
```

Good:

```python
if call.args is None:
    raise ValueError(f"Tool call '{call.name}' did not include arguments")

args = tool.args_model.model_validate(call.args)
```

The same applies to other defensive fallbacks:

- avoid silent defaults when required runtime data is missing
- avoid broad "recover and continue" patterns unless they are intentional UX choices
- prefer loud boundary failures over hidden compensation

This keeps the code honest and easier to reason about.

## Dependencies

Dependencies like Exa clients and databases should live on `AgentContext`.

Tool availability should be controlled by the agent, not by defensive checks scattered throughout handlers.

Example:

- if search is only valid when `context.exa` exists, only register or expose the search tool when Exa is configured
- do not register the tool and then make the handler compensate for missing dependencies

This keeps handlers focused on tool behavior.

## Prompt Construction

Introduce a small `PromptBuilder`.

Responsibilities:

- build system prompt from config and run state
- inject mode and todo context consistently
- later allow Jinja templates if prompts become more complex

Keep Jinja as an implementation detail of prompt construction, not as a central runtime abstraction.

## Subagents

Support subagents by giving each subagent:

- its own `RunConfig`
- its own `RunState`
- shared or scoped dependencies via `AgentContext`

This naturally supports:

- explicit iteration budgets per subagent
- separate mode/todo state
- a live block in the shell for each subagent

## Suggested File Layout

- `agent.py`
  Core lifecycle, hook execution, tool dispatch.
- `state.py`
  `RunConfig`, `RunState`, `AgentContext`.
- `tools.py`
  Tool definitions and handlers.
- `prompts.py`
  Prompt builder.
- `shell.py`
  Generic writing plus live block support.

Workshop variants can then differ mainly by:

- which hooks are registered
- which tools are available
- what prompt text is used

instead of re-defining the whole runtime in each file.

## Migration Plan

1. Extract shared `RunConfig`, `RunState`, and `AgentContext`.
2. Replace subclass-based tools with `Tool` specs plus plain handlers.
3. Move tool input validation to one runtime boundary and remove `args or {}` fallbacks.
4. Keep hooks, but reduce them to `before_model`, `after_model`, and `after_tools`.
5. Clean up rendering around `shell.write(...)` plus updateable blocks.
6. Move prompt assembly into a dedicated prompt builder.
7. Refactor workshop variants to reuse the shared runtime instead of copying it.

## Success Criteria

- The main agent loop is readable in one pass.
- Hooks remain easy to explain in the workshop.
- Tool handlers receive validated typed inputs.
- Missing required tool args cause immediate errors instead of silent defaults.
- Rendering stays flexible without introducing a reducer architecture.
- Subagents can have independent iteration budgets and live UI blocks.
