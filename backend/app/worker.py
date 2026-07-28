import asyncio
import json
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from celery import Celery
from croniter import croniter
from sqlalchemy import select

from app.core.config import get_settings
from app.core.database import SessionLocal, engine
from app.models.entities import Workflow, WorkflowApproval, WorkflowRun, WorkflowVersion
from app.services.model_providers import load_model_provider_runtimes
from app.services.workflow_engine import WorkflowPause, execute_graph
from app.services.workflow_environment import build_system_variables, load_workflow_environment

settings = get_settings()
celery = Celery("openworkflow", broker=settings.redis_url, backend=settings.redis_url)
celery.conf.update(
    task_track_started=True,
    task_serializer="json",
    result_serializer="json",
    beat_schedule={"dispatch-workflow-schedules": {"task": "workflow.dispatch_schedules", "schedule": 60.0}},
)


@celery.task(name="system.ping")
def ping() -> str:
    return "pong"


@celery.task(name="workflow.dispatch_schedules")
def dispatch_schedules() -> int:
    return asyncio.run(_dispatch_schedules_and_dispose())


async def _dispatch_schedules_and_dispose() -> int:
    try:
        return await _dispatch_schedules()
    finally:
        # Celery creates a fresh event loop for each task invocation. Asyncpg
        # connections cannot be reused by the next loop.
        await engine.dispose()


async def _dispatch_schedules() -> int:
    now = datetime.now(UTC)
    dispatched = 0
    async with SessionLocal() as db:
        workflows = list(
            (
                await db.scalars(
                    select(Workflow).where(
                        Workflow.published_version_id.is_not(None),
                        Workflow.deleted_at.is_(None),
                    )
                )
            ).all()
        )
        for workflow in workflows:
            version = await db.get(WorkflowVersion, workflow.published_version_id)
            if not version:
                continue
            start = next((node for node in version.graph.get("nodes", []) if node.get("type") == "start"), None)
            config = start.get("data", {}).get("config", {}) if start else {}
            schedule = config.get("schedule", {})
            if "schedule" not in config.get("triggers", []) or not schedule.get("enabled", True):
                continue
            local_now = now.astimezone(ZoneInfo(schedule.get("timezone", "UTC")))
            if not croniter.match(schedule.get("cron", ""), local_now):
                continue
            minute_start = now.replace(second=0, microsecond=0)
            existing = await db.scalar(
                select(WorkflowRun).where(
                    WorkflowRun.workflow_id == workflow.id,
                    WorkflowRun.workflow_version_id == version.id,
                    WorkflowRun.triggered_by == "schedule",
                    WorkflowRun.created_at >= minute_start,
                )
            )
            if existing:
                continue
            inputs = json.loads(schedule.get("inputs_json", "{}"))
            run = WorkflowRun(
                workspace_id=workflow.workspace_id,
                workflow_id=workflow.id,
                workflow_version_id=version.id,
                status="running",
                triggered_by="schedule",
                inputs=inputs,
            )
            db.add(run)
            await db.flush()
            try:
                environment = await load_workflow_environment(db, workflow.workspace_id, workflow.id)
                model_providers = await load_model_provider_runtimes(db, workflow.workspace_id)
                system = build_system_variables(workflow_id=workflow.id, run_id=run.id)
                run.outputs, run.trace = execute_graph(
                    version.graph,
                    inputs,
                    environment=environment,
                    system=system,
                    model_providers=model_providers,
                )
                run.status = "succeeded"
                run.finished_at = datetime.now(UTC)
            except WorkflowPause as pause:
                approval = WorkflowApproval(
                    workspace_id=workflow.workspace_id,
                    workflow_id=workflow.id,
                    run_id=run.id,
                    node_id=pause.node_id,
                    request=pause.request,
                    graph=deepcopy(version.graph),
                    resume_state=pause.resume_state,
                    expires_at=datetime.now(UTC) + timedelta(minutes=int(pause.request.get("timeout_minutes", 4320))),
                )
                db.add(approval)
                await db.flush()
                run.status = "waiting"
                run.trace = [*pause.resume_state.get("trace", []), {"node_id": pause.node_id, "node_type": "human", "status": "waiting", "output": {"approval_id": approval.id}, "error": None, "attempts": 0, "error_handled": False, "started_at": datetime.now(UTC).isoformat(), "finished_at": None}]
            except Exception as exc:
                run.status = "failed"
                run.error = str(exc)
                run.finished_at = datetime.now(UTC)
            dispatched += 1
        await db.commit()
    return dispatched
