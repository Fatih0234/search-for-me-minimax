from google.genai import Client, types

client = Client()


read_file_tool = types.Tool(
    function_declarations=[
        types.FunctionDeclaration(
            name="readFile",
            description="Read the contents of a file from disk",
            parameters=types.Schema(
                type="OBJECT",
                properties={
                    "path": types.Schema(
                        type="STRING", description="Path to the file to read"
                    )
                },
                required=["path"],
            ),
        )
    ]
)

response = client.models.generate_content(
    model="gemini-3.1-pro-preview",
    contents="Read the readme",
    config=types.GenerateContentConfig(
        system_instruction="""
You are Koroku, a coding agent built by Ivan.

Be polite, positive and helpful where you can.
""",
        tools=[read_file_tool],
        thinking_config=types.ThinkingConfig(thinking_level="LOW"),
    ),
)

print(response)
