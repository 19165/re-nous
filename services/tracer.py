import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy import select
from db.database import AsyncSessionLocal
from db.models import TraceStep
from config import redis_client, is_redis_available
from utils.logger import logger
from schemas import TraceStepSchema

class Tracer:
    """
    Service for step-level audit tracing and live SSE event broadcasting.
    Persists audit records permanently in PostgreSQL and broadcasts progress to Redis Pub/Sub.
    """

    @staticmethod
    async def record_step(
        run_id: str,
        step_index: int,
        agent_name: str,
        input_data: Optional[Dict[str, Any]] = None,
        output_data: Optional[Dict[str, Any]] = None,
        tools_called: Optional[List[str]] = None,
        tokens_used: int = 0,
        latency_ms: float = 0.0,
    ) -> None:
        """Records a single agent execution step into PostgreSQL."""
        try:
            async with AsyncSessionLocal() as session:
                step = TraceStep(
                    run_id=run_id,
                    step_index=step_index,
                    agent_name=agent_name,
                    input_data=input_data or {},
                    output_data=output_data or {},
                    tools_called=tools_called or [],
                    tokens_used=tokens_used,
                    latency_ms=latency_ms,
                    created_at=datetime.utcnow(),
                )
                session.add(step)
                await session.commit()
                logger.debug(f"⏱️ [Tracer] Saved step {step_index} for {agent_name} (Run ID: {run_id})")
        except Exception as e:
            logger.error(f"❌ [Tracer] Failed to record step for {agent_name}: {e}")

    @staticmethod
    async def get_trace_for_run(run_id: str) -> List[TraceStepSchema]:
        """Retrieves the complete step log for a given research run from PostgreSQL."""
        try:
            async with AsyncSessionLocal() as session:
                stmt = select(TraceStep).where(TraceStep.run_id == run_id).order_by(TraceStep.step_index.asc())
                result = await session.execute(stmt)
                steps = result.scalars().all()
                return [
                    TraceStepSchema(
                        step_index=s.step_index,
                        agent_name=s.agent_name,
                        input_data=s.input_data,
                        output_data=s.output_data,
                        tools_called=s.tools_called or [],
                        tokens_used=s.tokens_used,
                        latency_ms=s.latency_ms,
                        created_at=s.created_at.isoformat() if s.created_at else None,
                    )
                    for s in steps
                ]
        except Exception as e:
            logger.error(f"❌ [Tracer] Failed to fetch trace for run '{run_id}': {e}")
            return []

    @staticmethod
    def publish_progress_event(run_id: str, event_type: str, data: Dict[str, Any]) -> None:
        """
        Publishes a real-time progress event to Redis Pub/Sub for SSE streaming subscribers.
        """
        if not is_redis_available or redis_client is None:
            return

        channel = f"run:{run_id}:events"
        payload = {
            "run_id": run_id,
            "event": event_type,
            "data": data,
            "timestamp": datetime.utcnow().isoformat(),
        }
        try:
            redis_client.publish(channel, json.dumps(payload, default=str))
            logger.debug(f"📡 [SSE Event] Published '{event_type}' to channel {channel}")
        except Exception as e:
            logger.warning(f"⚠️ Failed to publish SSE event to Redis: {e}")
