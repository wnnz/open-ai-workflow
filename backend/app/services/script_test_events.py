import json
from collections.abc import AsyncIterator
from functools import lru_cache
from typing import Any

import redis
import redis.asyncio as async_redis

from app.core.config import get_settings

TTL_SECONDS = 86_400
TERMINAL_STATUSES = {"succeeded", "failed", "cancelled"}


@lru_cache
def client() -> redis.Redis:
    return redis.Redis.from_url(get_settings().redis_url, decode_responses=True)


def meta_key(task_id: str) -> str:
    return f"script:test:{task_id}:meta"


def payload_key(task_id: str) -> str:
    return f"script:test:{task_id}:payload"


def event_key(task_id: str) -> str:
    return f"script:test:{task_id}:events"


def create_script_test(
    task_id: str, workspace_id: str, script_id: str | None, payload: dict[str, Any]
) -> None:
    pipe = client().pipeline(transaction=False)
    pipe.hset(
        meta_key(task_id),
        mapping={"workspace_id": workspace_id, "script_id": script_id or "", "status": "pending"},
    )
    pipe.set(payload_key(task_id), json.dumps(payload, ensure_ascii=False), ex=TTL_SECONDS)
    pipe.expire(meta_key(task_id), TTL_SECONDS)
    pipe.execute()
    publish_script_test_event(task_id, {"type": "status", "status": "pending"})


def load_script_test_payload(task_id: str) -> dict[str, Any] | None:
    value = client().get(payload_key(task_id))
    return json.loads(value) if value else None


def get_script_test(task_id: str) -> dict[str, Any] | None:
    meta = client().hgetall(meta_key(task_id))
    if not meta:
        return None
    result = meta.get("result")
    return {**meta, "result": json.loads(result) if result else None}


def publish_script_test_event(task_id: str, event: dict[str, Any]) -> None:
    payload = json.dumps(event, ensure_ascii=False, default=str)
    pipe = client().pipeline(transaction=False)
    pipe.xadd(event_key(task_id), {"data": payload}, maxlen=2_000, approximate=True)
    pipe.expire(event_key(task_id), TTL_SECONDS)
    if event.get("type") == "status":
        pipe.hset(meta_key(task_id), "status", str(event.get("status", "running")))
        pipe.expire(meta_key(task_id), TTL_SECONDS)
    pipe.execute()


def finish_script_test(task_id: str, result: dict[str, Any]) -> None:
    status = str(result.get("status", "failed"))
    pipe = client().pipeline(transaction=False)
    pipe.hset(
        meta_key(task_id),
        mapping={"status": status, "result": json.dumps(result, ensure_ascii=False, default=str)},
    )
    pipe.expire(meta_key(task_id), TTL_SECONDS)
    pipe.delete(payload_key(task_id))
    pipe.execute()
    publish_script_test_event(task_id, {"type": "result", **result})


def cancel_script_test(task_id: str) -> None:
    pipe = client().pipeline(transaction=False)
    pipe.hset(meta_key(task_id), mapping={"status": "cancelled", "cancelled": "1"})
    pipe.delete(payload_key(task_id))
    pipe.expire(meta_key(task_id), TTL_SECONDS)
    pipe.execute()
    publish_script_test_event(task_id, {"type": "status", "status": "cancelled"})


def script_test_cancelled(task_id: str) -> bool:
    return client().hget(meta_key(task_id), "cancelled") == "1"


async def stream_script_test_events(task_id: str) -> AsyncIterator[str]:
    async_client = async_redis.Redis.from_url(get_settings().redis_url, decode_responses=True)
    last_id = "0-0"
    try:
        while True:
            batches = await async_client.xread({event_key(task_id): last_id}, count=100, block=15_000)
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
                    if event.get("type") == "result" or (
                        event.get("type") == "status" and event.get("status") == "cancelled"
                    ):
                        return
    finally:
        await async_client.aclose()
