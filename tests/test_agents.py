import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import argparse
from rich.panel import Panel
from agents.planning_agent import run_planner, PlanningAgent
from agents.research_agent import run_researcher, ResearchAgent
from agents.writer_agent import run_writer, WriterAgent
from utils.logger import console

def test_planner(query: str):
    console.print(Panel(f"[bold green]Starting Planner Test[/bold green]\nQuestion: [cyan]'{query}'[/cyan]", title="Planner Test"))
    try:
        console.print("[yellow]Invoking PlanningAgent...[/yellow]")
        result = run_planner(query)
        console.print("\n[bold green]Success! Planner returned structured output:[/bold green]")
        console.print(f"Original Question: [cyan]{result.original_question}[/cyan]")
        console.print("Sub-questions:")
        for idx, sq in enumerate(result.sub_questions, 1):
            console.print(f"  {idx}. [cyan]{sq}[/cyan]")
        return result
    except Exception as e:
        console.print(f"\n[bold red]Error running planner test:[/bold red] {e}")
        return None

if __name__ == "__main__":
    parser = argparse.ArgumentParser("Test Runner for Agents")
    parser.add_argument("--query", type=str, default="What is Agentic AI?", help="User's test query")
    args = parser.parse_args()
    test_planner(args.query)
