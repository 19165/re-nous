import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from orchestrators.research_orchestrator import app
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

# Ensure UTF-8
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

console = Console(force_terminal=True)

def visualize_graph():
    """Extracts and prints the Mermaid diagram and ASCII representation of the LangGraph workflow."""
    console.print(Panel("[bold green]🎨 LangGraph Workflow Visualization[/bold green]", title="Graph Visualizer"))
    
    try:
        mermaid_syntax = app.get_graph().draw_mermaid()
        console.print("[bold yellow]Mermaid Diagram Code:[/bold yellow]")
        console.print(Syntax(mermaid_syntax, "mermaid", theme="monokai", line_numbers=True))
        
        # Save mermaid markdown to docs
        docs_dir = PROJECT_ROOT / "docs"
        docs_dir.mkdir(exist_ok=True)
        mmd_file = docs_dir / "workflow_graph.mmd"
        with open(mmd_file, "w", encoding="utf-8") as f:
            f.write(mermaid_syntax)
        console.print(f"\n[bold green]✅ Saved Mermaid diagram to [cyan]{mmd_file}[/cyan][/bold green]")
        
    except Exception as e:
        console.print(f"[bold red]Failed to generate Mermaid graph:[/bold red] {e}")

    try:
        console.print("\n[bold yellow]ASCII Graph Representation:[/bold yellow]")
        app.get_graph().print_ascii()
    except Exception as e:
        console.print(f"[dim](ASCII representation not supported in current environment: {e})[/dim]")

if __name__ == "__main__":
    visualize_graph()
