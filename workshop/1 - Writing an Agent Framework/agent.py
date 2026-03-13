"""
See an example here of an agent which has a response fed to it and is able to respond to queries.

First turn: https://logfire-us.pydantic.dev/public-trace/2f236cc4-0a38-48e4-8c1e-d79bdccb45cf?spanId=eb60eb75ac37b798
Second turn: https://logfire-us.pydantic.dev/public-trace/51c7abaf-23a5-4734-b7e6-c9dc4ceb86aa?spanId=0e51b2189ec7ee5f
"""

from pydantic import BaseModel
from abc import ABC, abstractmethod
import re
from google.genai import types, Client
from typing import Any
import os
import logfire

os.environ["OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT"] = "true"

logfire.configure(console=False)
logfire.instrument_google_genai()


class ToolResult(BaseModel):
    error: bool
    name: str
    function_id: str
    response: dict[str, Any]

    model_config = {"arbitrary_types_allowed": True}

    def to_genai_part(self) -> types.Part:
        return types.Part(
            function_response=types.FunctionResponse(
                name=self.name, response=self.response, id=self.function_id
            )
        )


class AgentTool(BaseModel, ABC):
    @classmethod
    def tool_name(cls) -> str:
        name = cls.__name__
        parts = re.split(r"[_\s]+", name)
        if len(parts) > 1:
            return parts[0].lower() + "".join(part.capitalize() for part in parts[1:])
        return name[:1].lower() + name[1:]

    def tool_result(
        self, *, error: bool, function_id: str, response: dict[str, Any]
    ) -> ToolResult:
        return ToolResult(
            error=error,
            name=self.__class__.tool_name(),
            function_id=function_id,
            response=response,
        )

    @classmethod
    def to_genai_schema(cls) -> types.Tool:
        json_schema = cls.model_json_schema()
        tool_name = cls.tool_name()
        return types.Tool(
            function_declarations=[
                types.FunctionDeclaration(
                    name=tool_name,
                    description=json_schema.get("description", f"{tool_name} tool"),
                    parameters=types.Schema(
                        type="OBJECT",
                        properties=json_schema["properties"],
                        required=json_schema.get("required", []),
                    ),
                )
            ]
        )

    @abstractmethod
    def execute(self, function_id: str) -> ToolResult:
        raise NotImplementedError


class ReadFile(AgentTool):
    """
    Read the contents of a file from disk.
    """

    path: str

    def execute(self, function_id):
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                return self.tool_result(
                    error=False,
                    function_id=function_id,
                    response={"path": self.path, "content": f.read()},
                )
        except Exception as e:
            return self.tool_result(
                error=True,
                function_id=function_id,
                response={"path": self.path, "error": str(e)},
            )


SYSTEM_INSTRUCTION = """
You are Koroku, a coding agent built by Ivan.

Be polite, positive and helpful where you can.
"""


class Agent:
    def __init__(
        self,
        *,
        tools: list[type[AgentTool]],
        model: str = "gemini-3.1-pro-preview",
        system_instruction: str = SYSTEM_INSTRUCTION,
    ) -> None:
        self.client = Client()
        self.model = model
        self.system_instruction = system_instruction
        self.tool_registry = {tool.tool_name(): tool for tool in tools}

    def get_tools(self) -> list[types.Tool]:
        return [tool.to_genai_schema() for tool in self.tool_registry.values()]

    def execute_tool(self, tool_name: str, args: dict[str, Any], function_id: str) -> ToolResult:
        tool_cls = self.tool_registry.get(tool_name)
        if tool_cls is None:
            return ToolResult(
                error=True,
                name=tool_name,
                function_id=function_id,
                response={"error": f"Unknown tool: {tool_name}"},
            )

        try:
            tool_input = tool_cls.model_validate(args or {})
            return tool_input.execute(function_id=function_id)
        except Exception as e:
            return ToolResult(
                error=True,
                name=tool_name,
                function_id=function_id,
                response={"error": str(e)},
            )

    def run_until_idle(self, contents: list[types.Content | types.Part | list[types.Part]]) -> list[types.Part]:
        output_parts: list[types.Part] = []

        while True:
            response = self.client.models.generate_content(
                model=self.model,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=self.system_instruction,
                    tools=self.get_tools(),
                ),
            )

            message = response.candidates[0].content
            parts = message.parts or []
            contents.append(parts)
            output_parts.extend(parts)

            function_calls = [part.function_call for part in parts if part.function_call]
            if not function_calls:
                return output_parts

            tool_parts: list[types.Part] = []
            for call in function_calls:
                result = self.execute_tool(
                    tool_name=call.name,
                    args=call.args or {},
                    function_id=call.id,
                )
                tool_parts.append(result.to_genai_part())

            contents.append(tool_parts)


agent = Agent(tools=[ReadFile])
contents = []
while True:
    user_input = input("You: ")
    contents.append(types.Part.from_text(text=user_input))

    parts = agent.run_until_idle(contents)

    print("Assistant")

    for part in parts:
        if part.text:
            print(f"*: {part.text}")

        if part.function_call:
            print(f"[{part.function_call.name}]: {part.function_call.args}")
