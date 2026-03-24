from pathlib import Path

from google.genai import Client, types
from rich import print


def read_file(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


read_file_tool = types.Tool(
    function_declarations=[
        types.FunctionDeclaration(
            name="read_file",
            description="Read a UTF-8 text file and return its contents.",
            parameters=types.Schema(
                type="OBJECT",
                properties={
                    "path": types.Schema(
                        type="STRING",
                        description="Path to a UTF-8 text file.",
                    )
                },
                required=["path"],
            ),
        )
    ]
)


client = Client()

contents: list[types.Content] = [
    types.UserContent(
        parts=[types.Part.from_text(text="Please read the README.md file.")]
    )
]

completion = client.models.generate_content(
    model="gemini-3-flash-preview",
    contents=contents,
    config=types.GenerateContentConfig(tools=[read_file_tool]),
)

message = completion.candidates[0].content
print(message)

function_calls = [part.function_call for part in message.parts if part.function_call]

if not function_calls:
    raise RuntimeError("The model did not return a function call.")

if len(function_calls) != 1:
    raise RuntimeError(f"Expected exactly one function call, got {len(function_calls)}.")

call = function_calls[0]

if call.name != "read_file":
    raise RuntimeError(f"Unexpected tool call: {call.name}")

if call.args is None:
    raise RuntimeError("Tool call 'read_file' did not include arguments.")

path = call.args.get("path")
if not isinstance(path, str) or not path.strip():
    raise RuntimeError("Tool call 'read_file' is missing a valid 'path' argument.")

contents.append(message)
contents.append(
    types.UserContent(
        parts=[
            types.Part.from_function_response(
                name=call.name,
                response={
                    "path": path,
                    "content": read_file(path),
                },
            )
        ]
    )
)

follow_up = client.models.generate_content(
    model="gemini-3-flash-preview",
    contents=contents,
    config=types.GenerateContentConfig(tools=[read_file_tool]),
)

print()
print(follow_up.candidates[0].content)
