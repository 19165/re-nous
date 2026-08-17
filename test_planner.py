import sys
import argparse
from rich.console import Console
from rich.panel import Panel
from agents.planner import run_planner

# Initialize rich console
console = Console()

parser = argparse.ArgumentParser("A script for test planner agent")
# Adding Arguments
parser.add_argument("--query", type=str, help="User's query")


def test_planner(query: str):
    console.print(
        Panel(
            f"[bold green]Starting Planner Test[/bold green]\nQuestion: [cyan]'{query}'[/cyan]",
            title="Planner Test",
        )
    )

    try:
        # Run planner
        console.print(
            "[yellow]Invoking Planner agent (calling Ollama Cloud)...[/yellow]"
        )
        result = run_planner(query)

        # Display results
        console.print(
            "\n[bold green]Success! Planner returned structured output:[/bold green]"
        )
        console.print(f"Original Question: [cyan]{result.original_question}[/cyan]")
        console.print("Sub-questions:")
        for idx, sq in enumerate(result.sub_questions, 1):
            console.print(f"  {idx}. [cyan]{sq}[/cyan]")

    except Exception as e:
        console.print(f"\n[bold red]Error running planner test:[/bold red] {e}")
        sys.exit(1)


if __name__ == "__main__":
    args = parser.parse_args()
    test_planner(args.query)
