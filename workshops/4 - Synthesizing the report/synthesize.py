import warnings

from google.genai import Client
from rich import print
from rich.markdown import Markdown

warnings.filterwarnings(
    "ignore",
    message="Interactions usage is experimental and may change in future versions.",
    category=UserWarning,
)


SYNTHESIS_MODEL = "gemini-3.1-pro-preview"

write_report_tool = {
    "type": "function",
    "name": "write_report",
    "description": "Write the final research report.",
    "parameters": {
        "type": "object",
        "properties": {
            "report": {
                "type": "string",
                "description": "The complete research report in markdown format.",
            }
        },
        "required": ["report"],
    },
}


MOCK_REQUEST = "Deep research on the current state of quantum computing"

MOCK_RESULTS = [
    {
        "todo": "Research the current state of quantum error correction",
        "summary": "## Quantum Error Correction\n\nRecent advances in quantum error correction have been significant. Google's Willow chip demonstrated below-threshold error correction in late 2024, achieving exponential suppression of errors as code distance increases. Microsoft has also made progress with their topological approach, though practical topological qubits remain elusive.\n\nKey developments:\n- Surface codes remain the leading approach, with Google achieving a logical error rate of 10^-7\n- New LDPC codes show promise for reducing qubit overhead\n- Real-time decoding has improved dramatically, with sub-microsecond classical processing",
    },
    {
        "todo": "Compare superconducting vs trapped-ion qubit approaches",
        "summary": "## Qubit Technologies\n\nSuperconducting qubits (Google, IBM) offer fast gate times (~20ns) but shorter coherence times. Trapped-ion qubits (IonQ, Quantinuum) have longer coherence times and higher gate fidelities but slower operations.\n\nSuperconducting advantages: speed, manufacturability, integration with existing fab processes\nTrapped-ion advantages: all-to-all connectivity, higher two-qubit gate fidelity (>99.9%), longer coherence\n\nQuantinuum's H2 processor achieved a quantum volume of 65,536, while IBM's Heron processor focuses on error-mitigated utility-scale computation.",
    },
    {
        "todo": "Survey recent quantum advantage claims and their validity",
        "summary": "## Quantum Advantage\n\nGoogle's Willow processor (2024) performed a random circuit sampling task in under 5 minutes that would take classical supercomputers an estimated 10 septillion years. However, critics note that random circuit sampling has no practical application.\n\nMore practically relevant claims:\n- IBM demonstrated utility-scale quantum computation for materials simulation\n- Quantinuum showed advantage in certain optimization problems\n- QuEra demonstrated logical qubit operations with neutral atoms\n\nTrue practical quantum advantage for commercially relevant problems remains elusive but is expected within 3-5 years.",
    },
]


def synthesize_report(initial_request, subagent_results):
    client = Client()

    results_text = "\n\n---\n\n".join(
        f"### Research on: {r['todo']}\n\n{r['summary']}" for r in subagent_results
    )

    response = client.interactions.create(
        model=SYNTHESIS_MODEL,
        input=f"""
You are writing a final deep research report. Synthesize the research findings below into a single cohesive markdown report.

The report should have:
- A clear title
- An executive summary (3-4 sentences)
- Well-organized sections that synthesize (not just concatenate) the findings
- A conclusion with key takeaways

Call the write_report tool with the complete markdown report.

Original request: {initial_request}

Research findings:

{results_text}
""",
        tools=[write_report_tool],
    )

    function_call = next(
        (output for output in response.outputs if output.type == "function_call"),
        None,
    )

    return function_call.arguments["report"]


if __name__ == "__main__":
    print()
    print("[bold cyan]Synthesizing research report...[/bold cyan]")
    print()

    report = synthesize_report(MOCK_REQUEST, MOCK_RESULTS)

    print(Markdown(report))
