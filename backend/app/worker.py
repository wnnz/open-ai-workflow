import asyncio
import json
import logging
from copy import deepcopy
from datetime import UTC, datetime, timedelta

import httpx
from fastapi import HTTPException
from opentelemetry import trace
from sqlalchemy import select

from app.celery_app import celery
from app.core.config import get_settings
from app.core.database import SessionLocal, engine
from app.models.entities import Workflow, WorkflowApproval, WorkflowRun, WorkflowVersion
from app.observability import configure_logging, configure_otel, deliver_alert, record_node_event
from app.services.model_providers import load_model_provider_runtimes
from app.services.run_events import publish_run_event
from app.services.scheduling import next_schedule_at, schedule_inputs
from app.services.script_runtime import hydrate_script_resources
from app.services.script_test_events import (
    finish_script_test,
    load_script_test_payload,
    publish_script_test_event,
    script_test_cancelled,
)
from app.services.scripts import validate_inputs
from app.services.task_queue import enqueue_workflow_run
from app.services.workflow_engine import WorkflowPause, execute_graph
from app.services.workflow_environment import build_system_variables, load_workflow_environment
from app.services.workflow_files import (
    hydrate_file_references,
    materialize_generated_files,
    strip_internal_file_metadata,
)

logger = logging.getLogger(__name__)
configure_logging()
configure_otel("ordo-worker")


async def _run_and_dispose(coroutine):
    try:
        return await coroutine
    finally:
        await engine.dispose()


@celery.task(name="system.ping")
def ping() -> str:
    return "pong"


@celery.task(name="script.test")
def test_script(task_id: str) -> str:
    payload = load_script_test_payload(task_id)
    if not payload:
        return "missing"
    if script_test_cancelled(task_id):
        return "cancelled"
    publish_script_test_event(task_id, {"type": "status", "status": "running"})
    logs: list[str] = []
    result: dict = {
        "status": "failed",
        "outputs": {},
        "logs": logs,
        "error": "Sandbox returned no result",
        "elapsed_ms": 0,
    }
    try:
        with httpx.Client(timeout=float(payload.get("timeout_seconds", 30)) + 10) as client:
            with client.stream(
                "POST",
                f"{get_settings().sandbox_url}/execute/stream",
                json={**payload, "job_id": task_id},
                headers={"X-Sandbox-Token": get_settings().sandbox_shared_secret},
            ) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if not line:
                        continue
                    event = json.loads(line)
                    if event.get("type") == "log":
                        message = str(event.get("message", ""))
                        logs.append(message)
                        publish_script_test_event(task_id, event)
                    elif event.get("type") == "result":
                        result = {key: value for key, value in event.items() if key != "type"}
        if result.get("status") == "succeeded":
            outputs = result.get("outputs")
            if not isinstance(outputs, dict):
                raise ValueError("Python entrypoint must return an object")
            output_schema = payload.get("output_schema") or {}
            if output_schema:
                validate_inputs(output_schema, outputs)
    except (httpx.HTTPError, ValueError, HTTPException) as exc:
        result = {
            "status": "failed",
            "outputs": {},
            "error": str(getattr(exc, "detail", exc)),
            "elapsed_ms": result.get("elapsed_ms", 0),
        }
    if script_test_cancelled(task_id):
        result = {"status": "cancelled", "outputs": {}, "error": None, "elapsed_ms": result.get("elapsed_ms", 0)}
    result["logs"] = logs
    finish_script_test(task_id, result)
    return str(result["status"])


@celery.task(name="workflow.execute_run")
def execute_run(run_id: str, approval_id: str | None = None) -> str:
    return asyncio.run(_run_and_dispose(_execute_run(run_id, approval_id)))


async def _execute_run(run_id: str, approval_id: str | None = None) -> str:
    async with SessionLocal() as db:
        run = await db.get(WorkflowRun, run_id)
        if not run or run.status not in {"pending", "running"}:
            return "ignored"
        approval = await db.get(WorkflowApproval, approval_id) if approval_id else None
        graph = deepcopy(approval.graph if approval else run.execution_graph)
        resume_state = deepcopy(approval.resume_state) if approval else None
        run.status = "running"
        run.error = None
        await db.commit()
        publish_run_event(run.id, {"type": "run_started", "status": "running"})
        try:
            workflow = await db.get(Workflow, run.workflow_id)
            if not workflow:
                raise ValueError("Workflow not found")
            environment = await load_workflow_environment(db, run.workspace_id, run.workflow_id)
            model_providers = await load_model_provider_runtimes(db, run.workspace_id)
            hydrated_inputs = await hydrate_file_references(db, run.workspace_id, run.inputs)
            system = build_system_variables(
                workflow_id=run.workflow_id,
                run_id=run.id,
                user_id=run.trigger_user_id or run.created_by,
            )
            with trace.get_tracer(__name__).start_as_current_span(
                "workflow.run",
                attributes={"workflow.id": run.workflow_id, "run.id": run.id},
            ):
                outputs, node_trace = execute_graph(
                    graph,
                    hydrated_inputs,
                    resume_state=resume_state,
                    environment=environment,
                    system=system,
                    model_providers=model_providers,
                    event_callback=lambda event: (
                        record_node_event(event), publish_run_event(run.id, event)
                    ),
                )
            public_run = run.triggered_by in {"form", "api", "webhook"}
            run.outputs, run.trace = await materialize_generated_files(
                db,
                workspace_id=run.workspace_id,
                created_by=run.created_by or workflow.created_by,
                outputs=outputs,
                trace=node_trace,
                download_url=(
                    lambda file_id: f"/v1/apps/{workflow.slug}/runs/{run.id}/files/{file_id}"
                    if public_run
                    else f"/api/v1/workspaces/{run.workspace_id}/workflows/{run.workflow_id}/runs/{run.id}/files/{file_id}"
                ),
            )
            run.status = "succeeded"
            run.finished_at = datetime.now(UTC)
        except WorkflowPause as pause:
            waiting = WorkflowApproval(
                workspace_id=run.workspace_id,
                workflow_id=run.workflow_id,
                run_id=run.id,
                node_id=pause.node_id,
                request=pause.request,
                graph=graph,
                resume_state=pause.resume_state,
                expires_at=datetime.now(UTC)
                + timedelta(minutes=int(pause.request.get("timeout_minutes", 4320))),
            )
            db.add(waiting)
            await db.flush()
            run.status = "waiting"
            run.trace = strip_internal_file_metadata([
                *pause.resume_state.get("trace", []),
                {
                    "node_id": pause.node_id,
                    "node_type": "human",
                    "status": "waiting",
                    "output": {"approval_id": waiting.id},
                    "error": None,
                    "attempts": 0,
                    "error_handled": False,
                    "started_at": datetime.now(UTC).isoformat(),
                    "finished_at": None,
                },
            ])
        except Exception as exc:
            logger.exception("Workflow run failed", extra={"run_id": run.id})
            run.status = "failed"
            run.error = str(exc)
            run.finished_at = datetime.now(UTC)
        await db.commit()
        if run.status == "failed":
            deliver_alert(
                "workflow_run_failed",
                {
                    "run_id": run.id,
                    "workflow_id": run.workflow_id,
                    "error": run.error,
                },
            )
        publish_run_event(
            run.id,
            {
                "type": "run_finished",
                "status": run.status,
                "error": run.error,
            },
        )
        return run.status


@celery.task(name="workflow.dispatch_schedules")
def dispatch_schedules() -> int:
    return asyncio.run(_run_and_dispose(_dispatch_schedules()))


async def _dispatch_schedules() -> int:
    now = datetime.now(UTC)
    run_ids: list[str] = []
    async with SessionLocal() as db:
        workflows = list(
            (
                await db.scalars(
                    select(Workflow)
                    .where(
                        Workflow.published_version_id.is_not(None),
                        Workflow.deleted_at.is_(None),
                        Workflow.next_run_at.is_not(None),
                        Workflow.next_run_at <= now,
                    )
                    .order_by(Workflow.next_run_at)
                    .limit(100)
                    .with_for_update(skip_locked=True)
                )
            ).all()
        )
        for workflow in workflows:
            version = await db.get(WorkflowVersion, workflow.published_version_id)
            if not version:
                workflow.next_run_at = None
                continue
            try:
                inputs = schedule_inputs(version.graph)
                workflow.next_run_at = next_schedule_at(version.graph, now)
            except (TypeError, ValueError):
                logger.exception(
                    "Invalid workflow schedule", extra={"workflow_id": workflow.id}
                )
                workflow.next_run_at = None
                continue
            run = WorkflowRun(
                workspace_id=workflow.workspace_id,
                workflow_id=workflow.id,
                workflow_version_id=version.id,
                status="pending",
                triggered_by="schedule",
                inputs=inputs,
                execution_graph=await hydrate_script_resources(
                    db, version.graph, version.resolved_references
                ),
            )
            db.add(run)
            await db.flush()
            run_ids.append(run.id)
        await db.commit()
    for run_id in run_ids:
        await enqueue_workflow_run(run_id)
    return len(run_ids)
