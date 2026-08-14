import asyncio
from graph import app
from config import logger
from rich.pretty import pprint

async def run_system():
    # Example research topic
    question = "What are the key technological milestones achieved in fusion energy power plants in 2026?"
    
    logger.info("[bold green]🚀 Initializing Multi-Agent Research System...[/bold green]")
    logger.info(f"Research Topic: [cyan]'{question}'[/cyan]")
    
    try:
        # Execute the LangGraph workflow asynchronously
        final_state = await app.ainvoke({"question": question})
        
        logger.info("\n[bold green]🎉 Multi-Agent Workflow Completed successfully![/bold green]")
        logger.info("[bold green]Final Report Output Structure:[/bold green]")
        
        # Display the structured writer report dictionary using Rich pprint
        pprint(final_state.get("report", {}))
        
    except Exception as e:
        logger.exception(f"[bold red]An error occurred during workflow execution:[/bold red] {e}")

if __name__ == "__main__":
    # Run the async loop
    asyncio.run(run_system())
