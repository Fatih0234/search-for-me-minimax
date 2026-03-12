import os
import warnings

from exa_py import Exa
from google.genai import Client
from rich import print
from rich.markdown import Markdown

warnings.filterwarnings(
    "ignore",
    message="Interactions usage is experimental and may change in future versions.",
    category=UserWarning,
)


SUB_AGENT_MODEL = "gemini-3-flash-preview"

exa_search_tool = {
    "type": "function",
    "name": "exa_search",
    "description": "Search the web for information on a topic.",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query.",
            }
        },
        "required": ["query"],
    },
}

complete_research_tool = {
    "type": "function",
    "name": "complete_research",
    "description": "Submit the final research summary for this topic.",
    "parameters": {
        "type": "object",
        "properties": {
            "summary": {
                "type": "string",
                "description": "A detailed research summary in markdown with source URLs cited inline.",
            }
        },
        "required": ["summary"],
    },
}


def run_subagent(todo):
    client = Client()
    exa = Exa(api_key=os.environ["EXA_API_KEY"])
    previous_interaction_id = None

    response = client.interactions.create(
        model=SUB_AGENT_MODEL,
        input=f"""
You are a research sub-agent. Your job is to research this specific topic thoroughly:

{todo}

Use the exa_search tool to find relevant information. You may search multiple times with different queries to get comprehensive coverage.
When you have gathered enough information, call the complete_research tool with a detailed markdown summary that cites source URLs inline.
""",
        tools=[exa_search_tool, complete_research_tool],
        previous_interaction_id=previous_interaction_id,
    )
    previous_interaction_id = response.id

    while True:
        function_call = next(
            (output for output in response.outputs if output.type == "function_call"),
            None,
        )

        if not function_call:
            break

        if function_call.name == "complete_research":
            return function_call.arguments["summary"]

        if function_call.name == "exa_search":
            query = function_call.arguments["query"]
            print(f"  [dim]Searching: {query}[/dim]")

            results = exa.search(
                query,
                num_results=3,
                contents={"text": {"max_characters": 1000}},
            )

            result_text = "\n\n".join(
                f"Title: {r.title}\nURL: {r.url}\nContent: {r.text}"
                for r in results.results
            )

            response = client.interactions.create(
                model=SUB_AGENT_MODEL,
                input=[
                    {
                        "type": "function_result",
                        "call_id": function_call.id,
                        "name": function_call.name,
                        "result": result_text,
                    }
                ],
                tools=[exa_search_tool, complete_research_tool],
                previous_interaction_id=previous_interaction_id,
            )
            previous_interaction_id = response.id

    return response.outputs[-1].text


if __name__ == "__main__":
    MOCK_TODO = "Compare MCP vs traditional agent tool-use patterns for data retrieval"

    print()
    print(f"[bold cyan]Researching:[/bold cyan] {MOCK_TODO}")
    print()

    summary = run_subagent(MOCK_TODO)

    print("[bold green]Summary[/bold green]")
    print()
    print(Markdown(summary))
