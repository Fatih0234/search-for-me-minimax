import asyncio
from typing import Any

from google.genai import Client, types
from rich import print

from state import AgentContext, RunConfig, RunState
from tools import MODIFY_TODO_TOOL, READ_FILE_TOOL, Tool


class AgentRuntime:
    def __init__(
        self,
        *,
        config: RunConfig,
        state: RunState,
        context: AgentContext,
        tools: list[Tool],
    ) -> None:
        self.config = config
        self.state = state
        self.context = context
        self.tools = {tool.name: tool for tool in tools}

    def get_tools(self) -> list[types.Tool]:
        if self.state.iteration_count >= self.config.max_iterations:
            return []
        return [tool.to_genai_tool() for tool in self.tools.values()]

    async def execute_tool_call(
        self,
        call: types.FunctionCall,
    ) -> dict[str, Any]:
        tool = self.tools.get(call.name)
        if tool is None:
            raise RuntimeError(f"Unknown tool: {call.name}")

        if call.args is None:
            raise RuntimeError(f"Tool call '{call.name}' did not include arguments.")

        args = tool.args_model.model_validate(call.args)
        response = await tool.handler(args, self.state, self.context)
        return {"name": call.name, "response": response}


async def main() -> None:
    client = Client()
    config = RunConfig(max_iterations=5)
    state = RunState()
    context = AgentContext()
    runtime = AgentRuntime(
        config=config,
        state=state,
        context=context,
        tools=[READ_FILE_TOOL, MODIFY_TODO_TOOL],
    )

    contents: list[types.Content] = [
        types.UserContent(
            parts=[
                types.Part.from_text(
                    text=(
                        "First add a todo to read README.md, then read the README.md file."
                    )
                )
            ]
        )
    ]

    while True:
        state.iteration_count += 1
        print(
            {
                "iteration_count": state.iteration_count,
                "max_iterations": config.max_iterations,
                "todos": state.todos,
            }
        )

        completion = await client.aio.models.generate_content(
            model=config.model,
            contents=contents,
            config=types.GenerateContentConfig(tools=runtime.get_tools()),
        )

        message = completion.candidates[0].content
        print(message)
        contents.append(message)

        function_calls = [
            part.function_call for part in message.parts if part.function_call
        ]
        if not function_calls:
            break

        tool_parts: list[types.Part] = []
        for call in function_calls:
            result = await runtime.execute_tool_call(call)
            print(result["response"])
            tool_parts.append(
                types.Part.from_function_response(
                    name=result["name"],
                    response=result["response"],
                )
            )

        contents.append(types.UserContent(parts=tool_parts))


if __name__ == "__main__":
    asyncio.run(main())
