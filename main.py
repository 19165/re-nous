import asyncio
import argparse
import uuid
from typing import Optional
from rich.pretty import pprint
from orchestrators.research_orchestrator import app
from schemas import BudgetConfig
from config import default_budget
from utils.logger import logger

parser = argparse.ArgumentParser("Multi-Agent Research System CLI (Phase 4 with State Persistence & Cache)")
parser.add_argument("--query", type=str, required=True, help="User's research query")
parser.add_argument("--run-id", type=str, default=None, help="Session Run ID to resume an existing workflow (defaults to auto-generated UUID)")
parser.add_argument("--timeout", type=float, default=60.0, help="Wall-clock execution ceiling in seconds (default: 60.0)")
parser.add_argument("--max-sub-questions", type=int, default=3, help="Maximum sub-questions to investigate (default: 3)")
parser.add_argument("--max-tokens", type=int, default=16000, help="Estimated token ceiling (default: 16000)")

async def run_system(query: str, run_id: Optional[str], timeout: float, max_sub_questions: int, max_tokens: int):
    """Executes the Multi-Agent Research System with Supervisor, Budget controls, and State Persistence."""
    session_id = run_id or f"run-{uuid.uuid4().hex[:8]}"
    logger.info("[bold green]🚀 Initializing Multi-Agent Research System (Phase 4)...[/bold green]")
    logger.info(f"Research Topic: [cyan]'{query}'[/cyan]")
    logger.info(f"Session / Run ID: [magenta]{session_id}[/magenta]")
    
    # Custom runtime budget
    budget = BudgetConfig(
        max_sub_questions=max_sub_questions,
        max_total_tokens=max_tokens,
        wall_clock_timeout_seconds=timeout,
        max_revisions=1,
    )
    logger.info(f"Active Budgets: [dim]Timeout={timeout}s, Max Sub-Q={max_sub_questions}, Max Tokens={max_tokens}, Max Revisions=1[/dim]")

    try:
        # Execute the LangGraph workflow asynchronously with Checkpoint thread_id
        config = {"configurable": {"thread_id": session_id}}
        final_state = await app.ainvoke(
            {"question": query, "run_id": session_id, "budget": budget},
            config=config
        )

        logger.info("\n[bold green]🎉 Multi-Agent Workflow Completed successfully![/bold green]")
        if final_state.get("supervisor_feedback"):
            logger.info(f"Supervisor Evaluation Summary: [cyan]{final_state.get('supervisor_feedback')}[/cyan]")
            
        logger.info(f"Total Revision Loops: [magenta]{final_state.get('revision_count', 0)}[/magenta]")
        logger.info(f"Total Exact Tokens Used: [yellow]{final_state.get('total_tokens', 0)}[/yellow]")
        logger.info("[bold green]Final Report Output Structure:[/bold green]")

        # Display the structured writer report dictionary using Rich pprint
        pprint(final_state.get("report", {}))

    except Exception as e:
        logger.exception(f"[bold red]An error occurred during workflow execution:[/bold red] {e}")

if __name__ == "__main__":
    args = parser.parse_args()
    asyncio.run(run_system(
        query=args.query,
        run_id=args.run_id,
        timeout=args.timeout,
        max_sub_questions=args.max_sub_questions,
        max_tokens=args.max_tokens,
    ))

