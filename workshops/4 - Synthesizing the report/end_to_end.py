import sys
import warnings

from rich import print
from rich.markdown import Markdown

warnings.filterwarnings(
    "ignore",
    message="Interactions usage is experimental and may change in future versions.",
    category=UserWarning,
)

sys.path.insert(0, "workshops/1 - Generating our Research Plan")
sys.path.insert(0, "workshops/3 - Running sub-agents")
sys.path.insert(0, "workshops/4 - Synthesizing the report")

from google.genai import Client

from questions import run_clarification
from questions_with_plan import generate_plan_tool, PLANNING_MODEL
from fan_out import run_all_subagents
from synthesize import synthesize_report


if __name__ == "__main__":
    # Step 1: Clarification
    initial_request, clarification_history, response_text = run_clarification()

    print("[bold green]Research brief[/bold green]")
    print()
    print(Markdown(response_text))
    print()

    # Step 2: Generate plan
    client = Client()
    plan_response = client.interactions.create(
        model=PLANNING_MODEL,
        input=f"""
Create a structured research plan for this clarified deep research request.
Call the generate_plan tool exactly once.
Put a 3-4 sentence natural-language first response to the user in `response`.
That response should acknowledge what they want, restate the research focus clearly, and give a short TL;DR of the plan.
Put the actionable next steps in `todos` as a list of strings.
Do not reply with normal text.

Initial request: {initial_request}
Clarifications: {clarification_history}
Scoped summary: {response_text}
""",
        tools=[generate_plan_tool],
    )

    function_call = next(
        (output for output in plan_response.outputs if output.type == "function_call"),
        None,
    )

    print("[bold magenta]Plan[/bold magenta]")
    print()
    print(Markdown(function_call.arguments["response"]))
    print()

    todos = function_call.arguments["todos"]
    for todo in todos:
        print(f"[ ] {todo}")
    print()

    # Step 3: Run sub-agents
    print(f"[bold cyan]Running {len(todos)} sub-agents in parallel...[/bold cyan]")
    print()

    subagent_results = run_all_subagents(todos)
    print()

    # Step 4: Synthesize report
    print("[bold cyan]Synthesizing final report...[/bold cyan]")
    print()

    report = synthesize_report(initial_request, subagent_results)

    print(Markdown(report))
