import json
from datetime import UTC, datetime

import pytest

from app.middleware.body_limit import RequestBodyLimitMiddleware
from app.services import run_events
from app.services.scheduling import next_schedule_at


def http_scope(content_length: int | None = None) -> dict:
    headers = [] if content_length is None else [(b"content-length", str(content_length).encode())]
    return {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/upload",
        "raw_path": b"/upload",
        "query_string": b"",
        "headers": headers,
        "client": ("127.0.0.1", 1),
        "server": ("test", 80),
    }


async def invoke_body_limit(chunks: list[bytes], *, content_length: int | None = None) -> list[dict]:
    messages = [
        {"type": "http.request", "body": chunk, "more_body": index < len(chunks) - 1}
        for index, chunk in enumerate(chunks)
    ]
    sent: list[dict] = []

    async def receive() -> dict:
        return messages.pop(0)

    async def send(message: dict) -> None:
        sent.append(message)

    async def downstream(scope, receive, send) -> None:
        while True:
            message = await receive()
            if not message.get("more_body"):
                break
        await send({"type": "http.response.start", "status": 204, "headers": []})
        await send({"type": "http.response.body", "body": b""})

    middleware = RequestBodyLimitMiddleware(downstream, max_bytes=5)
    await middleware(http_scope(content_length), receive, send)
    return sent


@pytest.mark.asyncio
async def test_request_body_limit_rejects_content_length_and_chunked_bodies() -> None:
    early = await invoke_body_limit([b"ignored"], content_length=6)
    chunked = await invoke_body_limit([b"abc", b"def"])
    accepted = await invoke_body_limit([b"ab", b"cde"])
    assert early[0]["status"] == 413
    assert chunked[0]["status"] == 413
    assert accepted[0]["status"] == 204


@pytest.mark.asyncio
async def test_run_event_stream_replays_events_published_before_subscription(monkeypatch) -> None:
    events = [
        (
            "workflow:run:run-1",
            [
                ("1-0", {"data": json.dumps({"type": "token", "delta": "hello"})}),
                ("2-0", {"data": json.dumps({"type": "run_finished", "status": "succeeded"})}),
            ],
        )
    ]

    class Client:
        async def xread(self, streams, count, block):
            return events

        async def aclose(self):
            return None

    monkeypatch.setattr(run_events.async_redis.Redis, "from_url", lambda *args, **kwargs: Client())
    chunks = [item async for item in run_events.stream_run_events("run-1", "pending")]
    assert any('"delta": "hello"' in item for item in chunks)
    assert any('"type": "run_finished"' in item for item in chunks)


def test_next_schedule_at_uses_the_published_cron_timezone() -> None:
    graph = {
        "nodes": [
            {
                "type": "start",
                "data": {
                    "config": {
                        "triggers": ["schedule"],
                        "schedule": {
                            "enabled": True,
                            "cron": "0 9 * * *",
                            "timezone": "Asia/Singapore",
                        },
                    }
                },
            }
        ]
    }
    assert next_schedule_at(graph, datetime(2026, 7, 28, 0, 30, tzinfo=UTC)) == datetime(
        2026, 7, 28, 1, 0, tzinfo=UTC
    )
