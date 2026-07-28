import json
import logging
import sys
import time
import uuid
from contextvars import ContextVar

import httpx
from fastapi import FastAPI, Request, Response
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from redis import RedisError
from starlette.concurrency import run_in_threadpool

from app.core.config import get_settings
from app.services.run_events import publisher

request_id_context: ContextVar[str] = ContextVar("request_id", default="")
REQUEST_COUNT = Counter(
    "openworkflow_http_requests_total", "HTTP requests", ["method", "path", "status"]
)
REQUEST_DURATION = Histogram(
    "openworkflow_http_request_duration_seconds", "HTTP request duration", ["method", "path"]
)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": request_id_context.get(),
        }
        for field in ("run_id", "workflow_id", "node_id", "node_type", "duration_ms"):
            if hasattr(record, field):
                payload[field] = getattr(record, field)
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


def configure_logging() -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(get_settings().log_level.upper())
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        target = logging.getLogger(name)
        target.handlers = [handler]
        target.propagate = False


def deliver_alert(event: str, payload: dict) -> None:
    webhook = get_settings().alert_webhook_url
    if not webhook:
        return
    try:
        httpx.post(webhook, json={"event": event, **payload}, timeout=5).raise_for_status()
    except httpx.HTTPError:
        logging.getLogger(__name__).exception("Alert delivery failed")


def configure_otel(service_name: str, app: FastAPI | None = None) -> None:
    endpoint = get_settings().otel_exporter_otlp_endpoint
    if endpoint and not isinstance(trace.get_tracer_provider(), TracerProvider):
        provider = TracerProvider(resource=Resource.create({"service.name": service_name}))
        provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint)))
        trace.set_tracer_provider(provider)
    if app and endpoint:
        FastAPIInstrumentor.instrument_app(app)


def record_node_event(event: dict) -> None:
    if event.get("type") != "node_finished":
        return
    node_type = str(event.get("node_type", "unknown"))
    status = str(event.get("status", "unknown"))
    duration_ms = float(event.get("duration_ms", 0))
    if not get_settings().task_always_eager:
        try:
            metrics = publisher()
            metrics.hincrby("metrics:workflow:nodes:count", f"{node_type}:{status}", 1)
            metrics.hincrbyfloat("metrics:workflow:nodes:duration_ms", node_type, duration_ms)
        except RedisError:
            logging.getLogger(__name__).warning("Unable to record workflow node metrics", exc_info=True)
    trace.get_current_span().add_event("workflow.node", attributes={
        "node.id": str(event.get("node_id", "")),
        "node.type": node_type,
        "node.status": status,
        "node.duration_ms": duration_ms,
    })


def install_observability(app: FastAPI) -> None:
    configure_logging()
    configure_otel("openworkflow-api", app)

    @app.middleware("http")
    async def request_metrics(request: Request, call_next):
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        token = request_id_context.set(request_id)
        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception as exc:
            path = getattr(request.scope.get("route"), "path", request.url.path)
            REQUEST_COUNT.labels(request.method, path, "500").inc()
            await run_in_threadpool(
                deliver_alert,
                "api_request_failed",
                {
                    "method": request.method,
                    "path": path,
                    "request_id": request_id,
                    "error": str(exc),
                },
            )
            raise
        finally:
            path = getattr(request.scope.get("route"), "path", request.url.path)
            REQUEST_DURATION.labels(request.method, path).observe(time.perf_counter() - started)
            request_id_context.reset(token)
        REQUEST_COUNT.labels(request.method, path, str(response.status_code)).inc()
        response.headers["X-Request-ID"] = request_id
        return response

    @app.get("/metrics", include_in_schema=False)
    async def metrics() -> Response:
        body = bytearray(generate_latest())
        try:
            counts = publisher().hgetall("metrics:workflow:nodes:count")
            durations = publisher().hgetall("metrics:workflow:nodes:duration_ms")
        except RedisError:
            counts = {}
            durations = {}
        body.extend(b"# HELP openworkflow_workflow_nodes_total Executed workflow nodes\n")
        body.extend(b"# TYPE openworkflow_workflow_nodes_total counter\n")
        for key, value in counts.items():
            node_type, status = key.rsplit(":", 1)
            body.extend(f'openworkflow_workflow_nodes_total{{node_type="{node_type}",status="{status}"}} {value}\n'.encode())
        body.extend(b"# HELP openworkflow_workflow_node_duration_milliseconds_total Total node duration\n")
        body.extend(b"# TYPE openworkflow_workflow_node_duration_milliseconds_total counter\n")
        for node_type, value in durations.items():
            body.extend(f'openworkflow_workflow_node_duration_milliseconds_total{{node_type="{node_type}"}} {value}\n'.encode())
        return Response(bytes(body), media_type=CONTENT_TYPE_LATEST)
