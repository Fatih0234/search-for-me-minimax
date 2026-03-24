import asyncio
from typing import Any

from google.genai import Client, types
from rich import print

from tools import READ_FILE_TOOL, Tool


class AgentRuntime:
    def __init__(self, tools: list[Tool]) -> None:
        self.tools = {tool.name: tool for tool in tools}

    def get_tools(self) -> list[types.Tool]:
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
        response = await tool.handler(args)

        return {
            "name": call.name,
            "response": response,
        }


async def main() -> None:
    client = Client()
    runtime = AgentRuntime([READ_FILE_TOOL])

    contents: list[types.Content] = [
        types.UserContent(
            parts=[types.Part.from_text(text="Please read the README.md file.")]
        )
    ]

    completion = await client.aio.models.generate_content(
        model="gemini-3-flash-preview",
        contents=contents,
        config=types.GenerateContentConfig(tools=runtime.get_tools()),
    )

    message = completion.candidates[0].content
    print(message)

    function_calls = [part.function_call for part in message.parts if part.function_call]
    if not function_calls:
        raise RuntimeError("The model did not return a function call.")

    if len(function_calls) != 1:
        raise RuntimeError(f"Expected exactly one function call, got {len(function_calls)}.")

    tool_result = await runtime.execute_tool_call(function_calls[0])

    contents.append(message)
    contents.append(
        types.UserContent(
            parts=[
                types.Part.from_function_response(
                    name=tool_result["name"],
                    response=tool_result["response"],
                )
            ]
        )
    )

    follow_up = await client.aio.models.generate_content(
        model="gemini-3-flash-preview",
        contents=contents,
        config=types.GenerateContentConfig(tools=runtime.get_tools()),
    )

    print()
    print(follow_up.candidates[0].content)


if __name__ == "__main__":
    asyncio.run(main())
