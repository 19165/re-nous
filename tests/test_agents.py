import sys
import asyncio
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import argparse
from rich.panel import Panel
from rich.pretty import pprint
from agents.planning_agent import run_planner
from agents.research_agent import run_researcher
from agents.supervisor_agent import run_supervisor
from agents.writer_agent import run_writer
from schemas import BudgetConfig
from utils.logger import console

def test_planner(query: str):
    """Unit test for PlanningAgent."""
    console.print(Panel(f"[bold green]Starting Planner Test[/bold green]\nQuestion: [cyan]'{query}'[/cyan]", title="🧭 Planner Test"))
    try:
        console.print("[yellow]Invoking PlanningAgent...[/yellow]")
        result, tokens = run_planner(query)
        console.print("\n[bold green]✅ Success! Planner returned structured output:[/bold green]")
        console.print(f"Original Question: [cyan]{result.original_question}[/cyan]")
        console.print("Sub-questions:")
        for idx, sq in enumerate(result.sub_questions, 1):
            console.print(f"  {idx}. [cyan]{sq}[/cyan]")
        console.print(f"Exact Tokens Used: [yellow]{tokens}[/yellow]")
        return result
    except Exception as e:
        console.print(f"\n[bold red]❌ Error running planner test:[/bold red] {e}")
        return None

def test_researcher(sub_question: str, main_topic: str = ""):
    """Unit test for ResearchAgent."""
    console.print(Panel(f"[bold green]Starting Researcher Test[/bold green]\nMain Topic: [cyan]'{main_topic}'[/cyan]\nSub-question: [cyan]'{sub_question}'[/cyan]", title="🔍 Researcher Test"))
    try:
        console.print("[yellow]Invoking ResearchAgent (Query Optimization & Tavily search)...[/yellow]")
        result, tokens = asyncio.run(run_researcher(sub_question, main_topic))
        console.print("\n[bold green]✅ Success! Researcher returned structured sources:[/bold green]")
        console.print(f"Sub-question: [cyan]{result.sub_question}[/cyan]")
        console.print(f"Found {len(result.sources)} sources:")
        for idx, s in enumerate(result.sources, 1):
            console.print(f"  {idx}. [bold]{s.title}[/bold]\n     [dim]{s.url}[/dim]")
        console.print(f"Query Optimization Tokens Used: [yellow]{tokens}[/yellow]")
        return result
    except Exception as e:
        console.print(f"\n[bold red]❌ Error running researcher test:[/bold red] {e}")
        return None

def test_supervisor(query: str):
    """Unit test for SupervisorAgent evaluating mock findings."""
    console.print(Panel(f"[bold green]Starting Supervisor Test[/bold green]\nTopic: [cyan]'{query}'[/cyan]", title="🛡️ Supervisor Test"))
    try:
        mock_findings = [
            {
                "sub_question": f"Key architectures of {query}",
                "sources": [
                    {
                        "title": "Agentic Architectures",
                        "url": "https://example.com/arch",
                        "content": "Comprehensive details on autonomous agent loops and planning systems."
                    }
                ]
            },
            {
                "sub_question": f"Limitations and challenges of {query}",
                "sources": []  # Intentionally empty to test supervisor QA detection
            }
        ]
        console.print("[yellow]Invoking SupervisorAgent (Evaluating Findings & Budget)...[/yellow]")
        result, tokens = run_supervisor(
            question=query,
            findings=mock_findings,
            revision_count=0,
            elapsed_time=5.0,
            current_tokens=1000,
            budget=BudgetConfig()
        )
        console.print("\n[bold green]✅ Success! Supervisor returned structured evaluation:[/bold green]")
        appr_style = "bold green" if result.approved else "bold magenta"
        console.print(f"Approved: [{appr_style}]{result.approved}[/{appr_style}]")
        console.print(f"Reasoning: [cyan]{result.reasoning}[/cyan]")
        if result.sub_question_reviews:
            console.print(f"Sub-question Reviews ({len(result.sub_question_reviews)}):")
            for idx, rev in enumerate(result.sub_question_reviews, 1):
                console.print(f"  {idx}. [bold]{rev.sub_question}[/bold]")
                console.print(f"     Answered: {rev.is_answered} | Sources Sufficient: {rev.sources_sufficient}")
                if rev.refined_query:
                    console.print(f"     Refined Query: [yellow]{rev.refined_query}[/yellow]")
        console.print(f"Exact Tokens Used: [yellow]{tokens}[/yellow]")
        return result
    except Exception as e:
        console.print(f"\n[bold red]❌ Error running supervisor test:[/bold red] {e}")
        return None

def test_writer(query: str):
    """Unit test for WriterAgent using sample research findings."""
    console.print(Panel(f"[bold green]Starting Writer Test[/bold green]\nTopic: [cyan]'{query}'[/cyan]", title="📝 Writer Test"))
    try:
        sample_findings = [
            {
                "sub_question": "What is an AI Agent architecture?",
                "sources": [
                    {
                        "title": "Agentic AI Overview",
                        "url": "https://example.com/agent-overview",
                        "content": "AI agents utilize LLMs for planning, memory for state retention, and tools for environment execution."
                    }
                ]
            }
        ]
        console.print("[yellow]Invoking WriterAgent (Synthesizing Report)...[/yellow]")
        result, tokens = run_writer(query, sample_findings)
        console.print("\n[bold green]✅ Success! Writer returned structured report:[/bold green]")
        console.print(f"Title: [bold cyan]{result.title}[/bold cyan]")
        console.print(f"Summary: {result.summary}")
        console.print(f"Sections ({len(result.sections)}):")
        for s in result.sections:
            console.print(f"  • [bold]{s.section_title}[/bold]: {s.section_content[:120]}...")
        console.print(f"Citations: {result.citations}")
        console.print(f"Exact Tokens Used: [yellow]{tokens}[/yellow]")
        return result
    except Exception as e:
        console.print(f"\n[bold red]❌ Error running writer test:[/bold red] {e}")
        return None

def run_all_tests(query: str):
    """Runs tests for all 4 agents sequentially."""
    console.print(Panel("[bold magenta]🚀 Running All Agent Tests (Phase 2 Validation)[/bold magenta]", title="Full Agent Test Suite"))
    
    # 1. Planner
    planner_res = test_planner(query)
    
    # 2. Researcher
    sub_q = planner_res.sub_questions[0] if planner_res and planner_res.sub_questions else f"Key concepts of {query}"
    console.print("\n" + "─" * 60 + "\n")
    test_researcher(sub_q, main_topic=query)
    
    # 3. Supervisor
    console.print("\n" + "─" * 60 + "\n")
    test_supervisor(query)
    
    # 4. Writer
    console.print("\n" + "─" * 60 + "\n")
    test_writer(query)

if __name__ == "__main__":
    parser = argparse.ArgumentParser("Individual Test Runner for Specialist Agents")
    parser.add_argument(
        "--agent",
        type=str,
        choices=["planner", "researcher", "supervisor", "writer", "all"],
        default="all",
        help="Select which agent to test independently (planner, researcher, supervisor, writer, all)"
    )
    parser.add_argument(
        "--query",
        type=str,
        default="What is Agentic AI?",
        help="User's test query or research topic"
    )
    args = parser.parse_args()

    if args.agent == "planner":
        test_planner(args.query)
    elif args.agent == "researcher":
        test_researcher(args.query)
    elif args.agent == "supervisor":
        test_supervisor(args.query)
    elif args.agent == "writer":
        test_writer(args.query)
    elif args.agent == "all":
        run_all_tests(args.query)
