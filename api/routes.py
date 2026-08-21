import uuid
import asyncio
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, status
from sse_starlette.sse import EventSourceResponse

from schemas import (
    ResearchRequest,
    ResearchResponse,
    ResearchStatusResponse,
    TraceStepSchema,
    RunStatus,
    BudgetConfig,
)
from services.run_manager import RunManager
from services.tracer import Tracer
from orchestrators.research_orchestrator import app as research_app
from api.sse import sse_event_generator
from utils.logger import logger

router = APIRouter(prefix="/research", tags=["Research Multi-Agent System"])

async def execute_research_workflow(run_id: str, request: ResearchRequest) -> None:
    """
    Background worker that runs the LangGraph multi-agent workflow
    and manages state updates in PostgreSQL & Redis.
    """
    logger.info(f"🚀 [Background Task] Starting research workflow for [cyan]{run_id}[/cyan] ('{request.question}')")
    try:
        await RunManager.update_status(run_id, RunStatus.RUNNING)
        budget = BudgetConfig(
            max_sub_questions=request.max_sub_questions or 3,
            max_total_tokens=request.max_tokens or 16000,
            wall_clock_timeout_seconds=request.timeout or 60.0,
            max_revisions=1,
        )
        config = {"configurable": {"thread_id": run_id}}
        
        # Execute LangGraph asynchronously
        await research_app.ainvoke(
            {"question": request.question, "run_id": run_id, "budget": budget},
            config=config,
        )
        logger.info(f"✨ [Background Task] Completed research workflow for [cyan]{run_id}[/cyan]")
    except Exception as e:
        logger.exception(f"❌ [Background Task] Error in research workflow for {run_id}: {e}")
        await RunManager.update_status(run_id, RunStatus.FAILED, error_message=str(e))
        Tracer.publish_progress_event(run_id, "failed", {"error": str(e)})

@router.post(
    "",
    response_model=ResearchResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Submit a research question",
    description="Initializes an asynchronous multi-agent research workflow, returns a unique run_id immediately, and processes the job in the background."
)
async def submit_research(request: ResearchRequest) -> ResearchResponse:
    run_id = f"run-{uuid.uuid4().hex[:8]}"
    
    # 1. Persist initial PENDING record in PostgreSQL
    await RunManager.create_initial_run(run_id, request.question)
    
    # 2. Launch workflow asynchronously as background task
    asyncio.create_task(execute_research_workflow(run_id, request))
    
    return ResearchResponse(
        run_id=run_id,
        status=RunStatus.PENDING,
        message="Research job submitted successfully. Track status or stream progress using this run_id."
    )

@router.get(
    "/{id}",
    summary="Get research status & final report (supports SSE ?stream=true)",
    description="Retrieves the current progress and finished report. Pass `?stream=true` to receive real-time Server-Sent Events (SSE)."
)
async def get_research_status(
    id: str,
    stream: bool = Query(False, description="Set to true to stream real-time progress events via SSE")
):
    # If streaming is requested, return SSE EventSourceResponse
    if stream:
        return EventSourceResponse(sse_event_generator(id))
    
    # Standard JSON status query
    run_status = await RunManager.get_run_status(id)
    if not run_status:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Research run with ID '{id}' was not found."
        )
    return run_status

@router.get(
    "/{id}/trace",
    response_model=List[TraceStepSchema],
    summary="Get full step-level audit trace",
    description="Returns the chronological audit log of all agent steps (Planner, Researcher, Supervisor, Writer) including inputs, outputs, tools called, tokens, and latency."
)
async def get_research_trace(id: str) -> List[TraceStepSchema]:
    run_status = await RunManager.get_run_status(id)
    if not run_status:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Research run with ID '{id}' was not found."
        )
    
    trace_steps = await Tracer.get_trace_for_run(id)
    return trace_steps
