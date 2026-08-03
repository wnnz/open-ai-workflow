from datetime import UTC, datetime

from fastapi import APIRouter, File, Header, HTTPException, Request, UploadFile, status
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.deps import DbSession
from app.core.security import (
    create_app_access_token,
    decode_access_token,
    decode_app_access_token,
    token_hash,
    verify_password,
)
from app.models.entities import (
    ApiKey,
    StoredFile,
    User,
    Workflow,
    WorkflowAccessGrant,
    WorkflowRun,
    WorkflowVersion,
)
from app.schemas.workflow import RunIn
from app.services.public_guard import enforce_public_rate_limit
from app.services.run_control import (
    enqueue_persisted_workflow_run,
    ensure_public_run_capacity,
    find_idempotent_run,
    new_task_id,
    normalize_idempotency_key,
    request_fingerprint,
)
from app.services.run_events import stream_run_events
from app.services.script_runtime import hydrate_script_resources
from app.services.storage import object_path
from app.services.workflow_engine import validate_run_inputs
from app.services.workflow_files import (
    contains_file_id,
    create_uploaded_file,
    extend_file_retention,
    stored_file_available,
)

router = APIRouter(prefix="/apps", tags=["published apps"])


class AccessRequest(BaseModel):
    password: str = Field(default="", max_length=200)


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


def bearer_token(authorization: str | None, missing_detail: str) -> str:
    if not authorization:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, missing_detail)
    scheme, _, raw = authorization.partition(" ")
    if scheme.lower() != "bearer" or not raw:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid authorization header")
    return raw


async def authorize_api_key(
    db: DbSession, workflow: Workflow, authorization: str | None
) -> ApiKey | None:
    if workflow.published_access == "protected" and not authorization:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Bearer API key required")
    if not authorization:
        return None
    raw = bearer_token(authorization, "Bearer API key required")
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


def grant_is_active(grant: WorkflowAccessGrant) -> bool:
    expires_at = grant.expires_at
    if expires_at and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    return not expires_at or expires_at > datetime.now(UTC)


async def active_grants(db: DbSession, workflow: Workflow) -> list[WorkflowAccessGrant]:
    grants = list(
        (
            await db.scalars(
                select(WorkflowAccessGrant).where(
                    WorkflowAccessGrant.workflow_id == workflow.id
                )
            )
        ).all()
    )
    return [grant for grant in grants if grant_is_active(grant)]


async def authorize_form_user(
    db: DbSession, workflow: Workflow, authorization: str | None
) -> User | None:
    if workflow.published_access != "protected":
        return None
    raw = bearer_token(authorization, "Authentication required")
    try:
        user_id = decode_access_token(raw)
    except Exception as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid access token") from exc
    user = await db.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User is inactive")
    grants = await active_grants(db, workflow)
    if not any(
        grant.grant_type == "all_users"
        or (grant.grant_type == "user" and grant.user_id == user.id)
        for grant in grants
    ):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "User does not have access to this app")
    return user


async def authorize_password_grant(
    db: DbSession, workflow: Workflow, app_access: str | None
) -> WorkflowAccessGrant:
    if not app_access:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "App access password required")
    try:
        workflow_id, grant_id = decode_app_access_token(app_access)
    except Exception as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid app access token") from exc
    grant = await db.get(WorkflowAccessGrant, grant_id)
    if (
        workflow_id != workflow.id
        or not grant
        or grant.workflow_id != workflow.id
        or grant.grant_type != "password"
        or not grant_is_active(grant)
    ):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "App access has expired")
    return grant


async def authorize_form_access(
    db: DbSession,
    workflow: Workflow,
    authorization: str | None,
    app_access: str | None,
) -> User | WorkflowAccessGrant | None:
    if workflow.published_access != "protected":
        return None
    if app_access:
        return await authorize_password_grant(db, workflow, app_access)
    return await authorize_form_user(db, workflow, authorization)


async def authorize_run_access(
    db: DbSession,
    workflow: Workflow,
    authorization: str | None,
    app_access: str | None,
) -> ApiKey | User | WorkflowAccessGrant | None:
    if workflow.published_access != "protected":
        return None
    if app_access:
        return await authorize_password_grant(db, workflow, app_access)
    raw = bearer_token(authorization, "Authentication or app access required")
    if raw.startswith("owf_"):
        return await authorize_api_key(db, workflow, authorization)
    return await authorize_form_user(db, workflow, authorization)


def ensure_run_access(
    credential: ApiKey | User | WorkflowAccessGrant | None, run: WorkflowRun
) -> None:
    if isinstance(credential, User) and (
        run.triggered_by != "form" or run.trigger_user_id != credential.id
    ):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Workflow run not found")
    if isinstance(credential, WorkflowAccessGrant) and (
        run.triggered_by != "form" or run.trigger_user_id != f"grant:{credential.id}"
    ):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Workflow run not found")


def ensure_trigger(version: WorkflowVersion, trigger: str) -> None:
    start = next(node for node in version.graph["nodes"] if node.get("type") == "start")
    triggers = start.get("data", {}).get("config", {}).get("triggers", ["api"])
    if trigger not in triggers:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"{trigger.title()} trigger is not enabled")


@router.get("/{app_slug}")
async def describe_published(app_slug: str, db: DbSession) -> dict:
    workflow, version = await get_published(db, app_slug)
    grants = await active_grants(db, workflow) if workflow.published_access == "protected" else []
    start = next(node for node in version.graph["nodes"] if node.get("type") == "start")
    config = start.get("data", {}).get("config", {})
    return {
        "name": workflow.name,
        "description": workflow.description,
        "app_type": workflow.app_type,
        "access": workflow.published_access,
        "access_options": {
            "login": any(grant.grant_type in {"all_users", "user"} for grant in grants),
            "password": any(grant.grant_type == "password" for grant in grants),
        },
        "version": version.version,
        "triggers": config.get("triggers", ["api"]),
        "input_fields": config.get("input_fields", []),
    }


@router.post("/{app_slug}/access")
async def authorize_published_access(
    app_slug: str,
    payload: AccessRequest,
    db: DbSession,
    request: Request,
    authorization: str | None = Header(default=None),
    x_app_access: str | None = Header(default=None),
) -> dict:
    await enforce_public_rate_limit(request, app_slug, "access")
    workflow, _ = await get_published(db, app_slug)
    if workflow.published_access != "protected":
        return {"authorized": True}
    if x_app_access:
        grant = await authorize_password_grant(db, workflow, x_app_access)
        return {"authorized": True, "access_token": x_app_access, "grant_id": grant.id}
    if payload.password:
        password_grants = [
            grant for grant in await active_grants(db, workflow) if grant.grant_type == "password"
        ]
        grant = next(
            (
                item
                for item in password_grants
                if item.password_hash and verify_password(payload.password, item.password_hash)
            ),
            None,
        )
        if not grant:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired access password")
        return {
            "authorized": True,
            "access_token": create_app_access_token(workflow.id, grant.id, grant.expires_at),
            "grant_id": grant.id,
        }
    user = await authorize_form_user(db, workflow, authorization)
    return {"authorized": True, "user_id": user.id if user else None}


async def execute_published(
    app_slug: str,
    payload: RunIn,
    db: DbSession,
    authorization: str | None,
    app_access: str | None,
    triggered_by: str,
    idempotency_header: str | None,
) -> dict:
    workflow, version = await get_published(db, app_slug)
    credential: ApiKey | User | WorkflowAccessGrant | None
    if triggered_by == "form":
        credential = await authorize_form_access(db, workflow, authorization, app_access)
    else:
        credential = await authorize_api_key(db, workflow, authorization)
    idempotency_key = normalize_idempotency_key(idempotency_header)
    fingerprint = request_fingerprint(payload.inputs, payload.user)
    existing = await find_idempotent_run(
        db,
        workflow_id=workflow.id,
        triggered_by=triggered_by,
        idempotency_key=idempotency_key,
        fingerprint=fingerprint,
    )
    if existing:
        return public_run_response(existing, version.version)
    await ensure_public_run_capacity(db, workflow.id)
    execution_graph = await hydrate_script_resources(db, version.graph, version.resolved_references)
    validate_run_inputs(execution_graph, payload.inputs)
    await extend_file_retention(
        db,
        workflow.workspace_id,
        payload.inputs,
        purpose="public_run_input",
    )
    run = WorkflowRun(
        workspace_id=workflow.workspace_id,
        workflow_id=workflow.id,
        workflow_version_id=version.id,
        status="pending",
        triggered_by=triggered_by,
        trigger_user_id=(
            credential.id
            if isinstance(credential, User)
            else f"grant:{credential.id}"
            if isinstance(credential, WorkflowAccessGrant)
            else payload.user or None
        ),
        inputs=payload.inputs,
        execution_graph=execution_graph,
        task_id=new_task_id(),
        idempotency_key=idempotency_key,
        request_fingerprint=fingerprint if idempotency_key else None,
    )
    db.add(run)
    try:
        await db.flush()
        await db.commit()
    except IntegrityError:
        await db.rollback()
        existing = await find_idempotent_run(
            db,
            workflow_id=workflow.id,
            triggered_by=triggered_by,
            idempotency_key=idempotency_key,
            fingerprint=fingerprint,
        )
        if not existing:
            raise
        return public_run_response(existing, version.version)
    await enqueue_persisted_workflow_run(db, run)
    return public_run_response(run, version.version)


def public_run_response(run: WorkflowRun, version: int) -> dict:
    return {
        "run_id": run.id,
        "status": run.status,
        "version": version,
        "outputs": run.outputs,
        "trace": run.trace,
    }


@router.post("/{app_slug}/run")
async def run_published(
    app_slug: str,
    payload: RunIn,
    db: DbSession,
    request: Request,
    authorization: str | None = Header(default=None),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict:
    await enforce_public_rate_limit(request, app_slug, "run")
    _, version = await get_published(db, app_slug)
    ensure_trigger(version, "api")
    return await execute_published(
        app_slug, payload, db, authorization, None, "api", idempotency_key
    )


@router.post("/{app_slug}/form")
async def run_published_form(
    app_slug: str,
    payload: RunIn,
    db: DbSession,
    request: Request,
    authorization: str | None = Header(default=None),
    x_app_access: str | None = Header(default=None),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict:
    await enforce_public_rate_limit(request, app_slug, "run")
    _, version = await get_published(db, app_slug)
    ensure_trigger(version, "form")
    return await execute_published(
        app_slug,
        payload,
        db,
        authorization,
        x_app_access,
        "form",
        idempotency_key,
    )


@router.post("/{app_slug}/webhook")
async def webhook_published(
    app_slug: str,
    payload: RunIn,
    db: DbSession,
    request: Request,
    authorization: str | None = Header(default=None),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict:
    await enforce_public_rate_limit(request, app_slug, "run")
    workflow, version = await get_published(db, app_slug)
    ensure_trigger(version, "webhook")
    return await execute_published(
        app_slug,
        payload,
        db,
        authorization,
        None,
        "webhook",
        idempotency_key,
    )


@router.get("/{app_slug}/runs/{run_id}")
async def get_published_run(
    app_slug: str,
    run_id: str,
    db: DbSession,
    authorization: str | None = Header(default=None),
    x_app_access: str | None = Header(default=None),
) -> dict:
    workflow, version = await get_published(db, app_slug)
    credential = await authorize_run_access(db, workflow, authorization, x_app_access)
    run = await db.get(WorkflowRun, run_id)
    if not run or run.workflow_id != workflow.id or run.workflow_version_id != version.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Workflow run not found")
    ensure_run_access(credential, run)
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


@router.get("/{app_slug}/runs/{run_id}/files/{file_id}")
async def download_published_run_file(
    app_slug: str,
    run_id: str,
    file_id: str,
    db: DbSession,
    authorization: str | None = Header(default=None),
    x_app_access: str | None = Header(default=None),
) -> FileResponse:
    workflow, version = await get_published(db, app_slug)
    credential = await authorize_run_access(db, workflow, authorization, x_app_access)
    run = await db.get(WorkflowRun, run_id)
    stored = await db.get(StoredFile, file_id)
    if (
        not run
        or run.workflow_id != workflow.id
        or run.workflow_version_id != version.id
        or not stored
        or stored.workspace_id != workflow.workspace_id
        or not stored_file_available(stored)
        or not contains_file_id(run.outputs, file_id)
    ):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Workflow output file not found")
    ensure_run_access(credential, run)
    path = object_path(stored.object_key)
    if not path.is_file():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Workflow output file not found")
    return FileResponse(path, media_type=stored.content_type, filename=stored.filename)


@router.get("/{app_slug}/runs/{run_id}/events")
async def get_published_run_events(
    app_slug: str,
    run_id: str,
    db: DbSession,
    authorization: str | None = Header(default=None),
    x_app_access: str | None = Header(default=None),
) -> StreamingResponse:
    workflow, version = await get_published(db, app_slug)
    credential = await authorize_run_access(db, workflow, authorization, x_app_access)
    run = await db.get(WorkflowRun, run_id)
    if not run or run.workflow_id != workflow.id or run.workflow_version_id != version.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Workflow run not found")
    ensure_run_access(credential, run)
    return StreamingResponse(
        stream_run_events(run.id, run.status),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/{app_slug}/files", status_code=status.HTTP_201_CREATED)
async def upload_published_file(
    app_slug: str,
    db: DbSession,
    request: Request,
    file: UploadFile = File(...),
    authorization: str | None = Header(default=None),
    x_app_access: str | None = Header(default=None),
) -> dict:
    await enforce_public_rate_limit(request, app_slug, "upload")
    workflow, _ = await get_published(db, app_slug)
    await authorize_run_access(db, workflow, authorization, x_app_access)
    stored = await create_uploaded_file(
        db,
        workspace_id=workflow.workspace_id,
        created_by=workflow.created_by,
        file=file,
        purpose="public_run_input",
    )
    await db.commit()
    await db.refresh(stored)
    return {"id": stored.id, "filename": stored.filename, "content_type": stored.content_type, "size": stored.size}
