import asyncio
import argparse
from rich.pretty import pprint
from orchestrators.research_orchestrator import app
from utils.logger import logger

parser = argparse.ArgumentParser("Multi-Agent Research System CLI")
parser.add_argument("--query", type=str, required=True, help="User's research query")

async def run_system(query: str):
    """Executes the Multi-Agent Research System workflow."""
    logger.info("[bold green]🚀 Initializing Multi-Agent Research System...[/bold green]")
    logger.info(f"Research Topic: [cyan]'{query}'[/cyan]")

    try:
        # Execute the LangGraph workflow asynchronously
        final_state = await app.ainvoke({"question": query})

        logger.info("\n[bold green]🎉 Multi-Agent Workflow Completed successfully![/bold green]")
        logger.info("[bold green]Final Report Output Structure:[/bold green]")

        # Display the structured writer report dictionary using Rich pprint
        pprint(final_state.get("report", {}))

    except Exception as e:
        logger.exception(f"[bold red]An error occurred during workflow execution:[/bold red] {e}")

if __name__ == "__main__":
    args = parser.parse_args()
    asyncio.run(run_system(args.query))
