import os

from exa_py import Exa
from rich import print

exa = Exa(api_key=os.environ["EXA_API_KEY"])

results = exa.search(
    "latest developments in quantum computing 2025",
    num_results=3,
    contents={"text": {"max_characters": 1000}},
)

for r in results.results:
    print(f"[bold]{r.title}[/bold]")
    print(f"[dim]{r.url}[/dim]")
    print(r.text[:200])
    print()
