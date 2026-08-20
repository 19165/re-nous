import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from orchestrators.research_orchestrator import app, build_research_graph
from schemas import BudgetConfig
from utils.logger import console

def test_graph_compilation():
    """Validates that the research orchestrator compiles cleanly and includes Supervisor node."""
    graph = build_research_graph()
    assert graph is not None, "StateGraph failed to compile"
    node_keys = list(graph.nodes.keys())
    assert "planner" in node_keys, "Planner node missing in graph"
    assert "researcher" in node_keys, "Researcher node missing in graph"
    assert "supervisor" in node_keys, "Supervisor node missing in graph"
    assert "writer" in node_keys, "Writer node missing in graph"
    console.print("[bold green]✅ StateGraph with Supervisor node compiled and verified successfully![/bold green]")

if __name__ == "__main__":
    test_graph_compilation()
