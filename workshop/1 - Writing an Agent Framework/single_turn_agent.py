"""
See an example here of an agent which has a response fed to it and is able to respond to queries.

First turn: https://logfire-us.pydantic.dev/public-trace/8f01b41a-e9de-4412-954b-0a98d46c733e?spanId=f6468a1cfc1d28ed
Second turn: https://logfire-us.pydantic.dev/public-trace/570d7706-958e-41f4-974f-4c37a0f02bce?spanId=0dd3bff84ee3c783
"""

from pydantic import BaseModel
from abc import ABC, abstractmethod
import re
from google.genai import types, Client
from typing import Any, Awaitable
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
    def execute(self, function_id: str) -> Awaitable[ToolResult]:
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


client = Client()
contents = []
while True:
    user_input = input("You: ")
    contents.append(types.Part.from_text(text=user_input))

    response = client.models.generate_content(
        model="gemini-3.1-pro-preview",
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction="""
You are Koroku, a coding agent built by Ivan.

Be polite, positive and helpful where you can.
""",
            tools=[ReadFile.to_genai_schema()],
        ),
    )

    parts = response.candidates[0].content.parts
    contents.append(parts)

    print("Assistant")

    for part in parts:
        if part.text:
            print(f"*: {part.text}")

        if part.function_call:
            print(f"[{part.function_call.name}]: {part.function_call.args}")

            # Execute function
            fc_name = part.function_call.name
            if fc_name == "readFile":
                result = ReadFile(**part.function_call.args).execute(
                    function_id=part.function_call.id
                )
                contents.append(result.to_genai_part())
