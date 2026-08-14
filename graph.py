import operator
from typing import List, TypedDict, Annotated
from langgraph.graph import StateGraph, START, END
from langgraph.constants import Send

from schemas import PlannerOutput, ResearcherOutput, WriterOutput
from agents.planner import run_planner
from agents.researcher import run_researcher
from agents.writer import run_writer
from config import logger

# --- State Definitions ---

class WorkerState(TypedDict):
    """State passed to each parallel Researcher instance."""
    sub_question: str

class GraphState(TypedDict):
    """Main Orchestrator Graph State."""
    question: str
    sub_questions: List[str]
    # operator.add accumulates researcher outputs from parallel branches
    findings: Annotated[List[dict], operator.add]
    report: dict  # Serialized WriterOutput dictionary

# --- Async Nodes ---

async def planner_node(state: GraphState) -> dict:
    """Invokes the Planner agent and outputs sub-questions."""
    logger.info("[bold yellow]🧭 Running Planner Node...[/bold yellow]")
    planner_result: PlannerOutput = run_planner(state["question"])
    logger.info(f"Planner created sub-questions: [cyan]{planner_result.sub_questions}[/cyan]")
    return {"sub_questions": planner_result.sub_questions}

async def researcher_node(state: WorkerState) -> dict:
    """Invokes the Researcher agent asynchronously to search web."""
    sub_q = state["sub_question"]
    # We call and await the async researcher
    research_result: ResearcherOutput = await run_researcher(sub_q)
    return {"findings": [research_result.model_dump()]}

async def writer_node(state: GraphState) -> dict:
    """Invokes the Writer agent to compile the final report."""
    logger.info("[bold yellow]📝 Running Writer Node (Synthesizing Report)...[/bold yellow]")
    writer_result: WriterOutput = run_writer(state["question"], state["findings"])
    return {"report": writer_result.model_dump()}

# --- Routing Logic (Map-Reduce Send Pattern) ---

def route_to_researchers(state: GraphState) -> List[Send]:
    """Routes the output of the planner to parallel researcher instances."""
    return [Send("researcher", {"sub_question": q}) for q in state["sub_questions"]]

# --- Graph Assembly ---

workflow = StateGraph(GraphState)

# Add Nodes (LangGraph fully supports async nodes)
workflow.add_node("planner", planner_node)
workflow.add_node("researcher", researcher_node)
workflow.add_node("writer", writer_node)

# Set up Edges
workflow.add_edge(START, "planner")
workflow.add_conditional_edges("planner", route_to_researchers, ["researcher"])
workflow.add_edge("researcher", "writer")
workflow.add_edge("writer", END)

# Compile the graph
app = workflow.compile()
