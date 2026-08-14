import sys
from rich.console import Console
from rich.panel import Panel
from agents.planner import run_planner

# Initialize rich console
console = Console()

def test_planner():
    sample_question = "What are the key advancements and challenges of solid-state batteries in electric vehicles in 2026?"
    
    console.print(Panel(f"[bold green]Starting Planner Test[/bold green]\nQuestion: [cyan]'{sample_question}'[/cyan]", title="Planner Test"))
    
    try:
        # Run planner
        console.print("[yellow]Invoking Planner agent (calling Ollama Cloud)...[/yellow]")
        result = run_planner(sample_question)
        
        # Display results
        console.print("\n[bold green]Success! Planner returned structured output:[/bold green]")
        console.print(f"Original Question: [cyan]{result.original_question}[/cyan]")
        console.print("Sub-questions:")
        for idx, sq in enumerate(result.sub_questions, 1):
            console.print(f"  {idx}. [cyan]{sq}[/cyan]")
            
    except Exception as e:
        console.print(f"\n[bold red]Error running planner test:[/bold red] {e}")
        sys.exit(1)

if __name__ == "__main__":
    test_planner()
