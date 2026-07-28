import json
import logging
from collections.abc import AsyncIterator
from functools import lru_cache
from typing import Any

import redis
import redis.asyncio as async_redis

from app.core.config import get_settings

TERMINAL_STATUSES = {"succeeded", "failed", "waiting"}
logger = logging.getLogger(__name__)


def channel(run_id: str) -> str:
    return f"workflow:run:{run_id}"


@lru_cache
def publisher() -> redis.Redis:
    return redis.Redis.from_url(get_settings().redis_url, decode_responses=True)


def publish_run_event(run_id: str, event: dict[str, Any]) -> None:
    if get_settings().task_always_eager:
        return
    try:
        payload = json.dumps(event, ensure_ascii=False, default=str)
        publisher().pipeline(transaction=False).xadd(
            channel(run_id), {"data": payload}, maxlen=10_000, approximate=True
        ).expire(channel(run_id), 86_400).execute()
    except redis.RedisError:
        logger.warning("Unable to publish workflow run event", extra={"run_id": run_id}, exc_info=True)


async def stream_run_events(run_id: str, initial_status: str) -> AsyncIterator[str]:
    client = async_redis.Redis.from_url(get_settings().redis_url, decode_responses=True)
    try:
        yield f"data: {json.dumps({'type': 'status', 'status': initial_status})}\n\n"
        if initial_status in TERMINAL_STATUSES:
            return
        last_id = "0-0"
        while True:
            batches = await client.xread({channel(run_id): last_id}, count=100, block=15_000)
            if not batches:
                yield ": keep-alive\n\n"
                continue
            for _, entries in batches:
                for event_id, fields in entries:
                    last_id = event_id
                    payload = str(fields.get("data", ""))
                    if not payload:
                        continue
                    yield f"data: {payload}\n\n"
                    try:
                        event = json.loads(payload)
                    except ValueError:
                        continue
                    if event.get("type") == "run_finished":
                        return
    finally:
        await client.aclose()
