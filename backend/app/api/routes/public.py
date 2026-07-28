from copy import deepcopy
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, File, Header, HTTPException, UploadFile, status
from sqlalchemy import select
from starlette.concurrency import run_in_threadpool

from app.api.deps import DbSession
from app.core.config import get_settings
from app.core.security import token_hash
from app.models.entities import (
    ApiKey,
    StoredFile,
    Workflow,
    WorkflowApproval,
    WorkflowRun,
    WorkflowVersion,
)
from app.schemas.workflow import RunIn
from app.services.model_providers import load_model_provider_runtimes
from app.services.storage import put
from app.services.workflow_engine import WorkflowPause, execute_graph
from app.services.workflow_environment import build_system_variables, load_workflow_environment

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
    run = WorkflowRun(
        workspace_id=workflow.workspace_id,
        workflow_id=workflow.id,
        workflow_version_id=version.id,
        status="running",
        triggered_by=triggered_by,
        inputs=payload.inputs,
    )
    db.add(run)
    await db.flush()
    try:
        environment = await load_workflow_environment(db, workflow.workspace_id, workflow.id)
        model_providers = await load_model_provider_runtimes(db, workflow.workspace_id)
        system = build_system_variables(workflow_id=workflow.id, run_id=run.id, user_id=payload.user)
        outputs, trace = execute_graph(
            version.graph,
            payload.inputs,
            environment=environment,
            system=system,
            model_providers=model_providers,
        )
        run.status = "succeeded"
        run.outputs = outputs
        run.trace = trace
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
        run.trace = [
            *pause.resume_state.get("trace", []),
            {"node_id": pause.node_id, "node_type": "human", "status": "waiting", "output": {"approval_id": approval.id}, "error": None, "attempts": 0, "error_handled": False, "started_at": datetime.now(UTC).isoformat(), "finished_at": None},
        ]
    except ValueError as exc:
        run.status = "failed"
        run.error = str(exc)
        run.finished_at = datetime.now(UTC)
        await db.commit()
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
    except Exception as exc:
        run.status = "failed"
        run.error = str(exc)
        run.finished_at = datetime.now(UTC)
        await db.commit()
        raise
    else:
        run.finished_at = datetime.now(UTC)
    await db.commit()
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


@router.post("/{app_slug}/files", status_code=status.HTTP_201_CREATED)
async def upload_published_file(
    app_slug: str,
    db: DbSession,
    file: UploadFile = File(...),
    authorization: str | None = Header(default=None),
) -> dict:
    workflow, _ = await get_published(db, app_slug)
    await authorize(db, workflow, authorization)
    content = await file.read()
    if len(content) > get_settings().max_upload_bytes:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "File too large")
    key, digest = await run_in_threadpool(
        put,
        workflow.workspace_id,
        file.filename or "file",
        file.content_type or "application/octet-stream",
        content,
    )
    stored = StoredFile(
        workspace_id=workflow.workspace_id,
        object_key=key,
        filename=file.filename or "file",
        content_type=file.content_type or "application/octet-stream",
        size=len(content),
        sha256=digest,
        created_by=workflow.created_by,
    )
    db.add(stored)
    await db.commit()
    await db.refresh(stored)
    return {"id": stored.id, "filename": stored.filename, "content_type": stored.content_type, "size": stored.size}
