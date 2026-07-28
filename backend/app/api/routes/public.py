from datetime import UTC, datetime

from fastapi import APIRouter, File, Header, HTTPException, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select

from app.api.deps import DbSession
from app.core.config import get_settings
from app.core.security import token_hash
from app.models.entities import (
    ApiKey,
    StoredFile,
    Workflow,
    WorkflowRun,
    WorkflowVersion,
)
from app.schemas.workflow import RunIn
from app.services.run_events import stream_run_events
from app.services.script_runtime import hydrate_script_resources
from app.services.task_queue import enqueue_workflow_run
from app.services.uploads import store_upload
from app.services.workflow_engine import validate_run_inputs

router = APIRouter(prefix="/apps", tags=["published apps"])


async def get_published(db: DbSession, app_slug: str) -> tuple[Workflow, WorkflowVersion]:
    workflow = await db.scalar(
        select(Workflow).where(
            Workflow.slug == app_slug,
            Workflow.published_version_id.is_not(None),
            Workflow.deleted_at.is_(None),
        )
    )
    if not workflow:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Published application not found")
    version = await db.get(WorkflowVersion, workflow.published_version_id)
    return workflow, version


async def authorize(
    db: DbSession, workflow: Workflow, authorization: str | None
) -> ApiKey | None:
    if workflow.published_access == "protected" and not authorization:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Bearer API key required")
    if not authorization:
        return None
    scheme, _, raw = authorization.partition(" ")
    if scheme.lower() != "bearer" or not raw:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid authorization header")
    api_key = await db.scalar(
        select(ApiKey).where(
            ApiKey.key_hash == token_hash(raw),
            ApiKey.workspace_id == workflow.workspace_id,
            ApiKey.revoked_at.is_(None),
        )
    )
    if not api_key or (api_key.workflow_id and api_key.workflow_id != workflow.id):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid API key")
    api_key.last_used_at = datetime.now(UTC)
    return api_key


def ensure_trigger(version: WorkflowVersion, trigger: str) -> None:
    start = next(node for node in version.graph["nodes"] if node.get("type") == "start")
    triggers = start.get("data", {}).get("config", {}).get("triggers", ["api"])
    if trigger not in triggers:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"{trigger.title()} trigger is not enabled")


@router.get("/{app_slug}")
async def describe_published(app_slug: str, db: DbSession) -> dict:
    workflow, version = await get_published(db, app_slug)
    start = next(node for node in version.graph["nodes"] if node.get("type") == "start")
    config = start.get("data", {}).get("config", {})
    return {
        "name": workflow.name,
        "description": workflow.description,
        "app_type": workflow.app_type,
        "access": workflow.published_access,
        "version": version.version,
        "triggers": config.get("triggers", ["api"]),
        "input_fields": config.get("input_fields", []),
    }


async def execute_published(
    app_slug: str,
    payload: RunIn,
    db: DbSession,
    authorization: str | None,
    triggered_by: str,
) -> dict:
    workflow, version = await get_published(db, app_slug)
    await authorize(db, workflow, authorization)
    execution_graph = await hydrate_script_resources(db, version.graph, version.resolved_references)
    validate_run_inputs(execution_graph, payload.inputs)
    run = WorkflowRun(
        workspace_id=workflow.workspace_id,
        workflow_id=workflow.id,
        workflow_version_id=version.id,
        status="pending",
        triggered_by=triggered_by,
        trigger_user_id=payload.user or None,
        inputs=payload.inputs,
        execution_graph=execution_graph,
    )
    db.add(run)
    await db.flush()
    await db.commit()
    if await enqueue_workflow_run(run.id):
        await db.refresh(run)
    return {"run_id": run.id, "status": run.status, "version": version.version, "outputs": run.outputs, "trace": run.trace}


@router.post("/{app_slug}/run")
async def run_published(
    app_slug: str,
    payload: RunIn,
    db: DbSession,
    authorization: str | None = Header(default=None),
) -> dict:
    _, version = await get_published(db, app_slug)
    ensure_trigger(version, "api")
    return await execute_published(app_slug, payload, db, authorization, "api")


@router.post("/{app_slug}/webhook")
async def webhook_published(
    app_slug: str,
    payload: RunIn,
    db: DbSession,
    authorization: str | None = Header(default=None),
) -> dict:
    workflow, version = await get_published(db, app_slug)
    ensure_trigger(version, "webhook")
    return await execute_published(app_slug, payload, db, authorization, "webhook")


@router.get("/{app_slug}/runs/{run_id}")
async def get_published_run(
    app_slug: str,
    run_id: str,
    db: DbSession,
    authorization: str | None = Header(default=None),
) -> dict:
    workflow, version = await get_published(db, app_slug)
    await authorize(db, workflow, authorization)
    run = await db.get(WorkflowRun, run_id)
    if not run or run.workflow_id != workflow.id or run.workflow_version_id != version.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Workflow run not found")
    return {
        "run_id": run.id,
        "status": run.status,
        "version": version.version,
        "outputs": run.outputs,
        "trace": run.trace,
        "error": run.error,
        "created_at": run.created_at,
        "finished_at": run.finished_at,
    }


@router.get("/{app_slug}/runs/{run_id}/events")
async def get_published_run_events(
    app_slug: str,
    run_id: str,
    db: DbSession,
    authorization: str | None = Header(default=None),
) -> StreamingResponse:
    workflow, version = await get_published(db, app_slug)
    await authorize(db, workflow, authorization)
    run = await db.get(WorkflowRun, run_id)
    if not run or run.workflow_id != workflow.id or run.workflow_version_id != version.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Workflow run not found")
    return StreamingResponse(
        stream_run_events(run.id, run.status),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/{app_slug}/files", status_code=status.HTTP_201_CREATED)
async def upload_published_file(
    app_slug: str,
    db: DbSession,
    file: UploadFile = File(...),
    authorization: str | None = Header(default=None),
) -> dict:
    workflow, _ = await get_published(db, app_slug)
    await authorize(db, workflow, authorization)
    key, digest, size = await store_upload(
        workflow.workspace_id, file, get_settings().max_upload_bytes
    )
    stored = StoredFile(
        workspace_id=workflow.workspace_id,
        object_key=key,
        filename=file.filename or "file",
        content_type=file.content_type or "application/octet-stream",
        size=size,
        sha256=digest,
        created_by=workflow.created_by,
    )
    db.add(stored)
    await db.commit()
    await db.refresh(stored)
    return {"id": stored.id, "filename": stored.filename, "content_type": stored.content_type, "size": stored.size}
