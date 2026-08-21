import json
import asyncio
from typing import AsyncGenerator, Dict, Any
import redis.asyncio as aioredis
from config import REDIS_URL
from services.run_manager import RunManager
from schemas import RunStatus
from utils.logger import logger

async def sse_event_generator(run_id: str) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Subscribes to the Redis Pub/Sub channel for a given run_id and yields Server-Sent Events.
    If the run has already finished, yields the terminal event immediately.
    """
    # 1. Check current status in DB
    current_run = await RunManager.get_run_status(run_id)
    if current_run and current_run.status in [RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.BUDGET_EXCEEDED]:
        yield {
            "event": "status",
            "data": json.dumps({
                "run_id": run_id,
                "status": current_run.status.value,
                "report": current_run.report.model_dump() if current_run.report else None,
                "error": current_run.error_message,
            }),
        }
        return

    # 2. Yield initial pending/running notice
    if current_run:
        yield {
            "event": "status",
            "data": json.dumps({
                "run_id": run_id,
                "status": current_run.status.value,
                "question": current_run.question,
            }),
        }

    # 3. Connect to Redis Pub/Sub for live events
    channel_name = f"run:{run_id}:events"
    r = None
    pubsub = None
    try:
        r = aioredis.from_url(REDIS_URL, decode_responses=True)
        pubsub = r.pubsub()
        await pubsub.subscribe(channel_name)
        logger.info(f"📡 [SSE] Client subscribed to stream for [cyan]{run_id}[/cyan]")

        while True:
            # Poll for new messages with timeout to allow ping/heartbeat
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if message and message.get("type") == "message":
                data_str = message.get("data")
                try:
                    payload = json.loads(data_str)
                    event_type = payload.get("event", "message")
                    yield {
                        "event": event_type,
                        "data": json.dumps(payload),
                    }
                    if event_type in ["completed", "failed", "budget_exceeded"]:
                        logger.info(f"📡 [SSE] Terminal event '{event_type}' reached for [cyan]{run_id}[/cyan]. Closing stream.")
                        break
                except Exception as parse_err:
                    yield {"event": "message", "data": data_str}

            await asyncio.sleep(0.1)

    except asyncio.CancelledError:
        logger.info(f"📡 [SSE] Client disconnected from stream [cyan]{run_id}[/cyan]")
    except Exception as e:
        logger.warning(f"⚠️ [SSE] Error streaming events for {run_id}: {e}")
        yield {
            "event": "error",
            "data": json.dumps({"error": str(e)}),
        }
    finally:
        if pubsub:
            try:
                await pubsub.unsubscribe(channel_name)
                await pubsub.close()
            except Exception:
                pass
        if r:
            try:
                await r.close()
            except Exception:
                pass
