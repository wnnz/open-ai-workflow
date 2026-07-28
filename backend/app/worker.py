import asyncio
import logging
from copy import deepcopy
from datetime import UTC, datetime, timedelta

from opentelemetry import trace
from sqlalchemy import select

from app.celery_app import celery
from app.core.database import SessionLocal, engine
from app.models.entities import Workflow, WorkflowApproval, WorkflowRun, WorkflowVersion
from app.observability import configure_logging, configure_otel, deliver_alert, record_node_event
from app.services.model_providers import load_model_provider_runtimes
from app.services.run_events import publish_run_event
from app.services.scheduling import next_schedule_at, schedule_inputs
from app.services.script_runtime import hydrate_script_resources
from app.services.task_queue import enqueue_workflow_run
from app.services.workflow_engine import WorkflowPause, execute_graph
from app.services.workflow_environment import build_system_variables, load_workflow_environment

logger = logging.getLogger(__name__)
configure_logging()
configure_otel("openworkflow-worker")


async def _run_and_dispose(coroutine):
    try:
        return await coroutine
    finally:
        await engine.dispose()


@celery.task(name="system.ping")
def ping() -> str:
    return "pong"


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
            environment = await load_workflow_environment(db, run.workspace_id, run.workflow_id)
            model_providers = await load_model_provider_runtimes(db, run.workspace_id)
            system = build_system_variables(
                workflow_id=run.workflow_id,
                run_id=run.id,
                user_id=run.trigger_user_id or run.created_by,
            )
            with trace.get_tracer(__name__).start_as_current_span(
                "workflow.run",
                attributes={"workflow.id": run.workflow_id, "run.id": run.id},
            ):
                run.outputs, run.trace = execute_graph(
                    graph,
                    run.inputs,
                    resume_state=resume_state,
                    environment=environment,
                    system=system,
                    model_providers=model_providers,
                    event_callback=lambda event: (
                        record_node_event(event), publish_run_event(run.id, event)
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
            run.trace = [
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
            ]
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
