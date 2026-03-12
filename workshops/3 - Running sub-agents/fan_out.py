from concurrent.futures import ThreadPoolExecutor, as_completed

from rich import print
from rich.markdown import Markdown

from subagent import run_subagent


MOCK_TODOS = [
    "Research the current state of quantum error correction techniques and recent breakthroughs",
    "Compare superconducting vs trapped-ion qubit approaches for scalable quantum computing",
    "Survey recent quantum advantage claims and their validity",
]


def run_all_subagents(todos):
    results = []
    with ThreadPoolExecutor() as executor:
        futures = {executor.submit(run_subagent, todo): todo for todo in todos}
        for future in as_completed(futures):
            todo = futures[future]
            summary = future.result()
            print(f"[bold green]✓[/bold green] {todo[:80]}...")
            results.append({"todo": todo, "summary": summary})
    return results


if __name__ == "__main__":
    print()
    print(f"[bold cyan]Running {len(MOCK_TODOS)} sub-agents in parallel...[/bold cyan]")
    print()

    results = run_all_subagents(MOCK_TODOS)

    print()
    for r in results:
        print(f"[bold magenta]{r['todo']}[/bold magenta]")
        print()
        print(Markdown(r["summary"]))
        print()
