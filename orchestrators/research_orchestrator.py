import time
import operator
from typing import List, Dict, Any, TypedDict, Annotated, Optional, Union
from langgraph.graph import StateGraph, START, END
from langgraph.constants import Send
from langgraph.checkpoint.memory import MemorySaver

from schemas import (
    PlannerOutput,
    ResearcherOutput,
    WriterOutput,
    SupervisorOutput,
    BudgetConfig,
)
from config import default_budget
from agents.planning_agent import run_planner
from agents.research_agent import run_researcher
from agents.supervisor_agent import run_supervisor
from agents.writer_agent import run_writer
from utils.logger import logger
from utils.redis_cache import get_cached_node_result, set_cached_node_result
from utils.citation_validator import validate_report_citations
from services.tracer import Tracer
from services.run_manager import RunManager

# --- Findings Merger Reducer (Per-Subquestion Aggregation & URL Deduplication) ---

def merge_findings_reducer(
    existing: List[Dict[str, Any]], new_items: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Reducer that appends and merges researcher findings per sub-question.
    Deduplicates URLs strictly within each individual sub-question context,
    allowing different sub-questions to independently reference the same authoritative sources.
    """
    if not existing and not new_items:
        return []
        
    combined = list(existing or []) + list(new_items or [])
    findings_map: Dict[str, Dict[str, Any]] = {}
    
    for item in combined:
        sq = item.get("sub_question", "")
        status = item.get("status", "SUCCESS")
        err = item.get("error_message")
        
        if sq not in findings_map:
            findings_map[sq] = {
                "sub_question": sq,
                "sources": [],
                "status": status,
                "error_message": err
            }
        else:
            if status:
                findings_map[sq]["status"] = status
                findings_map[sq]["error_message"] = err
        
        # Deduplicate URLs strictly per sub-question
        existing_urls = {s.get("url") for s in findings_map[sq]["sources"] if s.get("url")}
        for s in item.get("sources", []):
            url = s.get("url", "")
            if url and url in existing_urls:
                continue
            if url:
                existing_urls.add(url)
            findings_map[sq]["sources"].append(s)
            
    return list(findings_map.values())

# --- State Definitions ---

class WorkerState(TypedDict):
    """State passed to each parallel Researcher instance."""
    main_topic: str
    sub_question: str
    is_retry: bool
    run_id: Optional[str]

class GraphState(TypedDict):
    """Main Orchestrator State for the Multi-Agent State Machine."""
    question: str
    run_id: Optional[str]
    sub_questions: List[str]
    findings: Annotated[List[Dict[str, Any]], merge_findings_reducer]
    revision_count: int
    total_searches: Annotated[int, operator.add]
    total_tokens: Annotated[int, operator.add]
    start_time: float
    supervisor_feedback: Optional[str]
    supervisor_approved: bool
    sub_questions_to_retry: List[Dict[str, str]]
    budget: BudgetConfig
    report: Dict[str, Any]

# --- Async Graph Nodes ---

async def planner_node(state: GraphState) -> Dict[str, Any]:
    """Invokes Planner agent, applies sub-question limits, and initializes budget trackers with Redis caching & Tracing."""
    logger.info("[bold yellow]🧭 Running Planner Node...[/bold yellow]")
    step_start = time.time()
    active_budget = state.get("budget") or default_budget
    question = state["question"]
    run_id = state.get("run_id")

    if run_id:
        Tracer.publish_progress_event(run_id, "planner_started", {"question": question})

    # Check Redis Cache
    cached = get_cached_node_result("planner", question)
    if cached and "sub_questions" in cached:
        sub_qs = cached["sub_questions"][: active_budget.max_sub_questions]
        latency_ms = (time.time() - step_start) * 1000
        logger.info(f"⚡ [bold green]Planner Cache Hit:[/bold green] Retrieved [cyan]{len(sub_qs)}[/cyan] sub-questions from cache")
        if run_id:
            await Tracer.record_step(
                run_id=run_id,
                step_index=1,
                agent_name="Planner",
                input_data={"question": question},
                output_data={"sub_questions": sub_qs, "cache_hit": True},
                tools_called=[],
                tokens_used=0,
                latency_ms=latency_ms,
            )
            Tracer.publish_progress_event(run_id, "planner_completed", {"sub_questions": sub_qs, "cache_hit": True})

        return {
            "sub_questions": sub_qs,
            "start_time": time.time(),
            "revision_count": 0,
            "total_searches": 0,
            "total_tokens": 0,
            "supervisor_approved": False,
            "sub_questions_to_retry": [],
            "budget": active_budget,
        }

    planner_result, tokens = run_planner(question)
    sub_qs = planner_result.sub_questions[: active_budget.max_sub_questions]
    latency_ms = (time.time() - step_start) * 1000
    
    # Save to Redis Cache
    set_cached_node_result("planner", question, {"sub_questions": sub_qs})

    if run_id:
        await Tracer.record_step(
            run_id=run_id,
            step_index=1,
            agent_name="Planner",
            input_data={"question": question},
            output_data={"sub_questions": sub_qs},
            tools_called=[],
            tokens_used=tokens,
            latency_ms=latency_ms,
        )
        Tracer.publish_progress_event(run_id, "planner_completed", {"sub_questions": sub_qs, "tokens": tokens})

    logger.info(f"Planner created [cyan]{len(sub_qs)}[/cyan] sub-questions: [cyan]{sub_qs}[/cyan]")
    return {
        "sub_questions": sub_qs,
        "start_time": time.time(),
        "revision_count": 0,
        "total_searches": 0,
        "total_tokens": tokens,
        "supervisor_approved": False,
        "sub_questions_to_retry": [],
        "budget": active_budget,
    }

async def researcher_node(state: WorkerState) -> Dict[str, Any]:
    """Invokes Researcher agent with Query Optimization and tracks tokens/search count with Redis caching & Tracing."""
    step_start = time.time()
    sub_q = state["sub_question"]
    main_topic = state.get("main_topic", "")
    is_retry = state.get("is_retry", False)
    run_id = state.get("run_id")
    cache_input = f"{main_topic}::{sub_q}"

    if run_id:
        Tracer.publish_progress_event(run_id, "researcher_searching", {"sub_question": sub_q, "is_retry": is_retry})

    if is_retry:
        logger.info(f"🔄 [bold magenta]Researcher Node (2nd Pass/Retry):[/bold magenta] '{sub_q}'")
    else:
        logger.info(f"🔍 [bold cyan]Researcher Node (1st Pass):[/bold cyan] '{sub_q}'")

    # Check Redis Cache
    cached = get_cached_node_result("researcher", cache_input)
    if cached and "findings" in cached:
        latency_ms = (time.time() - step_start) * 1000
        logger.info(f"⚡ [bold green]Researcher Cache Hit:[/bold green] '{sub_q}'")
        if run_id:
            await Tracer.record_step(
                run_id=run_id,
                step_index=2,
                agent_name="Researcher",
                input_data={"sub_question": sub_q, "main_topic": main_topic, "is_retry": is_retry},
                output_data={"sources_count": len(cached["findings"][0].get("sources", [])), "cache_hit": True},
                tools_called=["tavily_search"],
                tokens_used=0,
                latency_ms=latency_ms,
            )
            Tracer.publish_progress_event(run_id, "researcher_completed", {"sub_question": sub_q, "sources_count": len(cached["findings"][0].get("sources", []))})

        return {
            "findings": cached["findings"],
            "total_searches": 0,
            "total_tokens": 0,
        }

    research_result, tokens = await run_researcher(sub_question=sub_q, main_topic=main_topic)
    findings_data = [research_result.model_dump()]
    latency_ms = (time.time() - step_start) * 1000

    # Save to Redis Cache
    set_cached_node_result("researcher", cache_input, {"findings": findings_data})

    if run_id:
        await Tracer.record_step(
            run_id=run_id,
            step_index=2,
            agent_name="Researcher",
            input_data={"sub_question": sub_q, "main_topic": main_topic, "is_retry": is_retry},
            output_data={"sources_count": len(research_result.sources), "status": research_result.status.value},
            tools_called=["tavily_search"],
            tokens_used=tokens,
            latency_ms=latency_ms,
        )
        Tracer.publish_progress_event(run_id, "researcher_completed", {"sub_question": sub_q, "sources_count": len(research_result.sources)})

    return {
        "findings": findings_data,
        "total_searches": 1,
        "total_tokens": tokens,
    }

async def supervisor_node(state: GraphState) -> Dict[str, Any]:
    """Evaluates researcher findings, enforces budgets, and decides if revision is needed with Redis caching & Tracing."""
    logger.info("[bold yellow]🛡️ Running Supervisor Node (QA & Budget Enforcement)...[/bold yellow]")
    step_start = time.time()
    active_budget = state.get("budget") or default_budget
    elapsed_time = time.time() - state.get("start_time", time.time())
    current_revision = state.get("revision_count", 0)
    current_tokens = state.get("total_tokens", 0)
    findings = state.get("findings", [])
    run_id = state.get("run_id")

    if run_id:
        Tracer.publish_progress_event(run_id, "supervisor_reviewing", {"revision_count": current_revision})

    cache_input = f"{state['question']}::rev_{current_revision}::{[s.get('sub_question', '') for s in findings]}"
    cached = get_cached_node_result("supervisor", cache_input)
    if cached:
        latency_ms = (time.time() - step_start) * 1000
        logger.info(f"⚡ [bold green]Supervisor Cache Hit[/bold green]")
        if run_id:
            await Tracer.record_step(
                run_id=run_id,
                step_index=3,
                agent_name="Supervisor",
                input_data={"findings_count": len(findings), "revision_count": current_revision},
                output_data={**cached, "cache_hit": True},
                tools_called=[],
                tokens_used=0,
                latency_ms=latency_ms,
            )
            Tracer.publish_progress_event(run_id, "supervisor_decision", {"approved": cached["supervisor_approved"], "reasoning": cached["supervisor_feedback"]})

        return {
            "supervisor_approved": cached["supervisor_approved"],
            "supervisor_feedback": cached["supervisor_feedback"],
            "sub_questions_to_retry": cached["sub_questions_to_retry"],
            "revision_count": cached["revision_count"],
            "total_tokens": 0,
        }

    supervisor_res, tokens = run_supervisor(
        question=state["question"],
        findings=findings,
        revision_count=current_revision,
        elapsed_time=elapsed_time,
        current_tokens=current_tokens,
        budget=active_budget
    )
    
    # Collect queries that need retry
    retry_list = []
    if not supervisor_res.approved and current_revision < active_budget.max_revisions:
        for review in supervisor_res.sub_question_reviews:
            if not review.is_answered or not review.sources_sufficient:
                retry_query = review.refined_query or review.sub_question
                retry_list.append({"original": review.sub_question, "query": retry_query})
        
        # If no specific review flagged, retry any with 0 sources or first failing
        if not retry_list and supervisor_res.sub_question_reviews:
            first_rev = supervisor_res.sub_question_reviews[0]
            retry_list.append({
                "original": first_rev.sub_question,
                "query": first_rev.refined_query or first_rev.sub_question
            })

    is_approved = supervisor_res.approved or (len(retry_list) == 0) or (current_revision >= active_budget.max_revisions)
    next_revision_count = current_revision + (1 if not is_approved else 0)
    latency_ms = (time.time() - step_start) * 1000
    
    result_to_cache = {
        "supervisor_approved": is_approved,
        "supervisor_feedback": supervisor_res.reasoning,
        "sub_questions_to_retry": retry_list if not is_approved else [],
        "revision_count": next_revision_count,
    }
    set_cached_node_result("supervisor", cache_input, result_to_cache)

    if run_id:
        await Tracer.record_step(
            run_id=run_id,
            step_index=3,
            agent_name="Supervisor",
            input_data={"findings_count": len(findings), "revision_count": current_revision},
            output_data=result_to_cache,
            tools_called=[],
            tokens_used=tokens,
            latency_ms=latency_ms,
        )
        Tracer.publish_progress_event(run_id, "supervisor_decision", {"approved": is_approved, "reasoning": supervisor_res.reasoning})

    return {
        **result_to_cache,
        "total_tokens": tokens,
    }

async def writer_node(state: GraphState) -> Dict[str, Any]:
    """Invokes Writer agent to synthesize all merged findings into the final report with Citation Validation & Permanent Storage."""
    logger.info("[bold yellow]📝 Running Writer Node (Synthesizing Final Report)...[/bold yellow]")
    step_start = time.time()
    findings = state.get("findings", [])
    run_id = state.get("run_id")
    cache_input = f"{state['question']}::{[(f.get('sub_question', ''), len(f.get('sources', []))) for f in findings]}"

    if run_id:
        Tracer.publish_progress_event(run_id, "writer_composing", {"findings_count": len(findings)})

    cached = get_cached_node_result("writer", cache_input)
    if cached and "report" in cached:
        latency_ms = (time.time() - step_start) * 1000
        logger.info(f"⚡ [bold green]Writer Cache Hit:[/bold green] Returning cached final report")
        report_dict = cached["report"]
        
        # Complete run in DB if run_id present
        if run_id:
            total_time = time.time() - state.get("start_time", time.time())
            await Tracer.record_step(
                run_id=run_id,
                step_index=4,
                agent_name="Writer",
                input_data={"findings_count": len(findings)},
                output_data={"report_title": report_dict.get("title"), "cache_hit": True},
                tools_called=[],
                tokens_used=0,
                latency_ms=latency_ms,
            )
            await RunManager.complete_run(
                run_id=run_id,
                report=report_dict,
                total_tokens=state.get("total_tokens", 0),
                total_searches=state.get("total_searches", 0),
                revision_count=state.get("revision_count", 0),
                execution_time_sec=total_time,
            )
            Tracer.publish_progress_event(run_id, "completed", {"title": report_dict.get("title"), "execution_time_sec": total_time})

        return {
            "report": report_dict,
            "total_tokens": 0,
        }

    writer_result, tokens = run_writer(state["question"], findings)
    
    # Run Citation Validation
    validated_report, warnings = validate_report_citations(writer_result, findings)
    report_dict = validated_report.model_dump()
    latency_ms = (time.time() - step_start) * 1000
    
    set_cached_node_result("writer", cache_input, {"report": report_dict})

    # Complete run in DB if run_id present
    if run_id:
        total_time = time.time() - state.get("start_time", time.time())
        final_tokens = state.get("total_tokens", 0) + tokens
        await Tracer.record_step(
            run_id=run_id,
            step_index=4,
            agent_name="Writer",
            input_data={"findings_count": len(findings)},
            output_data={"report_title": validated_report.title, "citations_count": len(validated_report.citations), "validation_warnings": warnings},
            tools_called=[],
            tokens_used=tokens,
            latency_ms=latency_ms,
        )
        await RunManager.complete_run(
            run_id=run_id,
            report=report_dict,
            total_tokens=final_tokens,
            total_searches=state.get("total_searches", 0),
            revision_count=state.get("revision_count", 0),
            execution_time_sec=total_time,
        )
        Tracer.publish_progress_event(run_id, "completed", {"title": validated_report.title, "execution_time_sec": total_time, "total_tokens": final_tokens})

    return {
        "report": report_dict,
        "total_tokens": tokens,
    }

# --- Routing Logic ---

def route_to_researchers(state: GraphState) -> List[Send]:
    """Initial fan-out from Planner to Researcher instances with main_topic context."""
    return [
        Send("researcher", {
            "main_topic": state["question"],
            "sub_question": q,
            "is_retry": False,
            "run_id": state.get("run_id"),
        })
        for q in state["sub_questions"]
    ]

def route_from_supervisor(state: GraphState) -> Union[List[Send], str]:
    """
    Conditional routing from Supervisor:
    - If approved or budget/revision limit reached -> route to 'writer'
    - If revision required -> Send failing queries back to 'researcher' with main_topic for exact-once retry
    """
    if state.get("supervisor_approved", False) or not state.get("sub_questions_to_retry"):
        logger.info("✅ [bold green]Supervisor Approved:[/bold green] Routing to Writer.")
        return "writer"
        
    retry_items = state["sub_questions_to_retry"]
    logger.info(f"🔄 [bold magenta]Supervisor Requested Revision ({len(retry_items)} queries):[/bold magenta] Routing back to Researcher.")
    return [
        Send("researcher", {
            "main_topic": state["question"],
            "sub_question": item["query"],
            "is_retry": True,
            "run_id": state.get("run_id"),
        })
        for item in retry_items
    ]


# --- Graph Assembly & Compilation ---

def build_research_graph(checkpointer: Optional[Any] = None) -> Any:
    """Builds and compiles the Multi-Agent Research StateGraph with Supervisor and Checkpointing."""
    workflow = StateGraph(GraphState)

    # Add Nodes
    workflow.add_node("planner", planner_node)
    workflow.add_node("researcher", researcher_node)
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("writer", writer_node)

    # Set up Edges
    workflow.add_edge(START, "planner")
    workflow.add_conditional_edges("planner", route_to_researchers, ["researcher"])
    workflow.add_edge("researcher", "supervisor")
    workflow.add_conditional_edges(
        "supervisor",
        route_from_supervisor,
        ["researcher", "writer"]
    )
    workflow.add_edge("writer", END)

    saver = checkpointer if checkpointer is not None else MemorySaver()
    return workflow.compile(checkpointer=saver)

# Default compiled application instance
app = build_research_graph()
