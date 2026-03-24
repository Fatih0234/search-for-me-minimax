from google.genai import Client, types
from rich import print


read_file_tool = types.Tool(
    function_declarations=[
        types.FunctionDeclaration(
            name="read_file",
            description="Read a text file and return its contents.",
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

completion = client.models.generate_content(
    model="gemini-3-flash-preview",
    contents=[
        types.UserContent(
            parts=[types.Part.from_text(text="Please read the README.md file.")]
        )
    ],
    config=types.GenerateContentConfig(tools=[read_file_tool]),
)

message = completion.candidates[0].content
function_calls = [part.function_call for part in message.parts if part.function_call]

print(message)

if function_calls:
    print("\nFunction calls:")
    for call in function_calls:
        print(f"- {call.name}")
        print(call.args)
