from copy import deepcopy
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from sqlalchemy import func, select
from starlette.concurrency import run_in_threadpool

from app.api.deps import CurrentUser, DbSession
from app.core.config import get_settings
from app.core.security import decrypt_secret, encrypt_secret
from app.models.entities import (
    Script,
    ScriptVersion,
    StoredFile,
    Workflow,
    WorkflowApproval,
    WorkflowEnvironmentVariable,
    WorkflowRun,
    WorkflowVersion,
)
from app.schemas.common import ApiModel
from app.schemas.workflow import (
    ApprovalOut,
    ApprovalResponseIn,
    PublishIn,
    RunIn,
    RunOut,
    WorkflowCreate,
    WorkflowEnvironmentVariableCreate,
    WorkflowEnvironmentVariableOut,
    WorkflowEnvironmentVariableUpdate,
    WorkflowOut,
    WorkflowUpdate,
    WorkflowVersionOut,
)
from app.services.model_providers import load_model_provider_runtimes
from app.services.storage import put
from app.services.workflow_engine import (
    WorkflowPause,
    execute_graph,
    execute_node_preview,
    resolve_script_references,
    validate_draft_graph,
    validate_graph,
    validate_run_inputs,
)
from app.services.workflow_environment import build_system_variables, load_workflow_environment
from app.services.workspaces import audit, require_role, slugify

router = APIRouter(prefix="/workspaces/{workspace_id}/workflows", tags=["workflows"])

DEFAULT_GRAPH = {
    "schema_version": 1,
    "nodes": [
        {
            "id": "start",
            "type": "start",
            "position": {"x": 80, "y": 160},
            "data": {
                "label": "Start",
                "config": {
                    "triggers": ["form"],
                    "input_fields": [
                        {
                            "name": "message",
                            "label": "Message",
                            "type": "text",
                            "required": False,
                            "placeholder": "",
                            "default_value": "",
                            "max_length": 2000,
                        }
                    ],
                    "schedule": {"cron": "0 9 * * *", "timezone": "UTC", "enabled": False, "inputs_json": "{}"},
                },
            },
        },
        {
            "id": "end",
            "type": "end",
            "position": {"x": 420, "y": 160},
            "data": {
                "label": "End",
                "config": {
                    "outputs": [
                        {
                            "name": "message",
                            "type": "String",
                            "value": "{{inputs.message}}",
                        }
                    ]
                },
            },
        },
    ],
    "edges": [{"id": "start-end", "source": "start", "target": "end"}],
}


class WorkflowFileOut(ApiModel):
    id: str
    filename: str
    content_type: str
    size: int


async def get_workflow(db: DbSession, workspace_id: str, workflow_id: str) -> Workflow:
    workflow = await db.get(Workflow, workflow_id)
    if not workflow or workflow.workspace_id != workspace_id or workflow.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Workflow not found")
    return workflow


async def resolve_subworkflow_references(
    db: DbSession,
    workspace_id: str,
    graph: dict,
    *,
    published: bool,
    ancestors: tuple[str, ...],
) -> tuple[dict, dict[str, dict]]:
    """Embed workspace-scoped child graphs so runs never perform unscoped lookups."""
    resolved_graph = deepcopy(graph)
    references: dict[str, dict] = {}
    for node in resolved_graph.get("nodes", []):
        if node.get("type") != "subworkflow":
            continue
        config = node.setdefault("data", {}).setdefault("config", {})
        target_id = str(config.get("workflow_id") or "")
        if not target_id:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Sub-workflow is required")
        if target_id in ancestors:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Sub-workflow cycle detected")
        target = await db.get(Workflow, target_id)
        if not target or target.workspace_id != workspace_id or target.deleted_at is not None:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Sub-workflow not found")
        if published:
            version = await db.get(WorkflowVersion, target.published_version_id) if target.published_version_id else None
            if not version or version.workspace_id != workspace_id or version.workflow_id != target.id:
                raise HTTPException(
                    status.HTTP_422_UNPROCESSABLE_CONTENT,
                    f"Sub-workflow '{target.name}' must be published first",
                )
            child_graph = deepcopy(version.graph)
            reference = {
                "workflow_id": target.id,
                "workflow_name": target.name,
                "workflow_version_id": version.id,
                "version": version.version,
            }
        else:
            child_graph, _ = await resolve_subworkflow_references(
                db,
                workspace_id,
                target.draft_graph,
                published=False,
                ancestors=(*ancestors, target.id),
            )
            reference = {
                "workflow_id": target.id,
                "workflow_name": target.name,
                "draft_version": target.draft_version,
            }
        config["workflow_name"] = target.name
        config["_resolved_graph"] = child_graph
        config["_resolved_reference"] = reference
        references[str(node["id"])] = reference
    return resolved_graph, references


async def set_run_waiting(
    db: DbSession,
    run: WorkflowRun,
    graph: dict,
    pause: WorkflowPause,
) -> WorkflowApproval:
    timeout_minutes = int(pause.request.get("timeout_minutes", 4320))
    approval = WorkflowApproval(
        workspace_id=run.workspace_id,
        workflow_id=run.workflow_id,
        run_id=run.id,
        node_id=pause.node_id,
        request=pause.request,
        graph=deepcopy(graph),
        resume_state=pause.resume_state,
        expires_at=datetime.now(UTC) + timedelta(minutes=timeout_minutes),
    )
    db.add(approval)
    await db.flush()
    run.status = "waiting"
    run.outputs = {}
    run.trace = [
        *pause.resume_state.get("trace", []),
        {
            "node_id": pause.node_id,
            "node_type": "human",
            "status": "waiting",
            "output": {"approval_id": approval.id, "expires_at": approval.expires_at.isoformat()},
            "error": None,
            "attempts": 0,
            "error_handled": False,
            "started_at": datetime.now(UTC).isoformat(),
            "finished_at": None,
        },
    ]
    run.error = None
    run.finished_at = None
    return approval


@router.get("", response_model=list[WorkflowOut])
async def list_workflows(workspace_id: str, db: DbSession, user: CurrentUser) -> list[Workflow]:
    await require_role(db, workspace_id, user.id)
    return list(
        (
            await db.scalars(
                select(Workflow)
                .where(Workflow.workspace_id == workspace_id, Workflow.deleted_at.is_(None))
                .order_by(Workflow.updated_at.desc())
            )
        ).all()
    )


@router.post("", response_model=WorkflowOut, status_code=status.HTTP_201_CREATED)
async def create_workflow(
    workspace_id: str, payload: WorkflowCreate, db: DbSession, user: CurrentUser
) -> Workflow:
    await require_role(db, workspace_id, user.id, "editor")
    workflow = Workflow(
        workspace_id=workspace_id,
        name=payload.name,
        slug=payload.slug or slugify(payload.name),
        description=payload.description,
        app_type=payload.app_type,
        draft_graph=DEFAULT_GRAPH,
        created_by=user.id,
    )
    db.add(workflow)
    await db.flush()
    db.add(audit(workspace_id, user.id, "workflow.created", "workflow", workflow.id))
    await db.commit()
    await db.refresh(workflow)
    return workflow


@router.get("/{workflow_id}", response_model=WorkflowOut)
async def read_workflow(
    workspace_id: str, workflow_id: str, db: DbSession, user: CurrentUser
) -> Workflow:
    await require_role(db, workspace_id, user.id)
    return await get_workflow(db, workspace_id, workflow_id)


def environment_variable_out(variable: WorkflowEnvironmentVariable) -> dict:
    secret = variable.value_type == "secret"
    value = decrypt_secret(variable.encrypted_value)
    return {
        "id": variable.id,
        "name": variable.name,
        "value_type": variable.value_type,
        "value": "••••••••" if secret and value else ("" if secret else value),
        "has_value": bool(value),
        "description": variable.description,
        "created_at": variable.created_at,
        "updated_at": variable.updated_at,
    }


def validate_environment_value(value_type: str, value: str) -> None:
    if value_type == "number":
        try:
            float(value)
        except ValueError as exc:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Number environment variable requires a numeric value") from exc


@router.get("/{workflow_id}/environment-variables", response_model=list[WorkflowEnvironmentVariableOut])
async def list_environment_variables(workspace_id: str, workflow_id: str, db: DbSession, user: CurrentUser) -> list[dict]:
    await require_role(db, workspace_id, user.id)
    await get_workflow(db, workspace_id, workflow_id)
    variables = list((await db.scalars(select(WorkflowEnvironmentVariable).where(
        WorkflowEnvironmentVariable.workspace_id == workspace_id,
        WorkflowEnvironmentVariable.workflow_id == workflow_id,
    ).order_by(WorkflowEnvironmentVariable.created_at))).all())
    return [environment_variable_out(variable) for variable in variables]


@router.post("/{workflow_id}/environment-variables", response_model=WorkflowEnvironmentVariableOut, status_code=status.HTTP_201_CREATED)
async def create_environment_variable(workspace_id: str, workflow_id: str, payload: WorkflowEnvironmentVariableCreate, db: DbSession, user: CurrentUser) -> dict:
    await require_role(db, workspace_id, user.id, "editor")
    await get_workflow(db, workspace_id, workflow_id)
    if await db.scalar(select(WorkflowEnvironmentVariable.id).where(WorkflowEnvironmentVariable.workflow_id == workflow_id, WorkflowEnvironmentVariable.name == payload.name)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Environment variable name already exists")
    validate_environment_value(payload.value_type, payload.value)
    variable = WorkflowEnvironmentVariable(workspace_id=workspace_id, workflow_id=workflow_id, name=payload.name, value_type=payload.value_type, encrypted_value=encrypt_secret(payload.value), description=payload.description, created_by=user.id)
    db.add(variable)
    await db.flush()
    db.add(audit(workspace_id, user.id, "workflow.environment_variable_created", "workflow_environment_variable", variable.id))
    await db.commit()
    await db.refresh(variable)
    return environment_variable_out(variable)


@router.put("/{workflow_id}/environment-variables/{variable_id}", response_model=WorkflowEnvironmentVariableOut)
async def update_environment_variable(workspace_id: str, workflow_id: str, variable_id: str, payload: WorkflowEnvironmentVariableUpdate, db: DbSession, user: CurrentUser) -> dict:
    await require_role(db, workspace_id, user.id, "editor")
    await get_workflow(db, workspace_id, workflow_id)
    variable = await db.scalar(select(WorkflowEnvironmentVariable).where(WorkflowEnvironmentVariable.id == variable_id, WorkflowEnvironmentVariable.workspace_id == workspace_id, WorkflowEnvironmentVariable.workflow_id == workflow_id))
    if not variable:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Environment variable not found")
    duplicate = await db.scalar(select(WorkflowEnvironmentVariable.id).where(WorkflowEnvironmentVariable.workflow_id == workflow_id, WorkflowEnvironmentVariable.name == payload.name, WorkflowEnvironmentVariable.id != variable_id))
    if duplicate:
        raise HTTPException(status.HTTP_409_CONFLICT, "Environment variable name already exists")
    if payload.value is None and payload.value_type != variable.value_type:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "A new value is required when changing variable type")
    if payload.value is not None:
        validate_environment_value(payload.value_type, payload.value)
        variable.encrypted_value = encrypt_secret(payload.value)
    variable.name = payload.name
    variable.value_type = payload.value_type
    variable.description = payload.description
    db.add(audit(workspace_id, user.id, "workflow.environment_variable_updated", "workflow_environment_variable", variable.id))
    await db.commit()
    await db.refresh(variable)
    return environment_variable_out(variable)


@router.delete("/{workflow_id}/environment-variables/{variable_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_environment_variable(workspace_id: str, workflow_id: str, variable_id: str, db: DbSession, user: CurrentUser) -> None:
    await require_role(db, workspace_id, user.id, "editor")
    variable = await db.scalar(select(WorkflowEnvironmentVariable).where(WorkflowEnvironmentVariable.id == variable_id, WorkflowEnvironmentVariable.workspace_id == workspace_id, WorkflowEnvironmentVariable.workflow_id == workflow_id))
    if not variable:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Environment variable not found")
    await db.delete(variable)
    db.add(audit(workspace_id, user.id, "workflow.environment_variable_deleted", "workflow_environment_variable", variable_id))
    await db.commit()


@router.post("/{workflow_id}/files", response_model=WorkflowFileOut, status_code=status.HTTP_201_CREATED)
async def upload_workflow_file(
    workspace_id: str,
    workflow_id: str,
    db: DbSession,
    user: CurrentUser,
    file: UploadFile = File(...),
) -> StoredFile:
    await require_role(db, workspace_id, user.id)
    await get_workflow(db, workspace_id, workflow_id)
    content = await file.read()
    if len(content) > get_settings().max_upload_bytes:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "File too large")
    key, digest = await run_in_threadpool(
        put,
        workspace_id,
        file.filename or "file",
        file.content_type or "application/octet-stream",
        content,
    )
    stored = StoredFile(
        workspace_id=workspace_id,
        object_key=key,
        filename=file.filename or "file",
        content_type=file.content_type or "application/octet-stream",
        size=len(content),
        sha256=digest,
        created_by=user.id,
    )
    db.add(stored)
    await db.flush()
    db.add(audit(workspace_id, user.id, "workflow.file_uploaded", "file", stored.id))
    await db.commit()
    await db.refresh(stored)
    return stored


@router.put("/{workflow_id}", response_model=WorkflowOut)
async def update_workflow(
    workspace_id: str, workflow_id: str, payload: WorkflowUpdate, db: DbSession, user: CurrentUser
) -> Workflow:
    await require_role(db, workspace_id, user.id, "editor")
    workflow = await get_workflow(db, workspace_id, workflow_id)
    if workflow.draft_version != payload.expected_version:
        raise HTTPException(status.HTTP_409_CONFLICT, "Workflow was updated by another member")
    validate_draft_graph(payload.graph)
    workflow.draft_graph = payload.graph
    workflow.draft_version += 1
    if payload.name is not None:
        workflow.name = payload.name
    if payload.description is not None:
        workflow.description = payload.description
    db.add(audit(workspace_id, user.id, "workflow.updated", "workflow", workflow.id))
    await db.commit()
    await db.refresh(workflow)
    return workflow


@router.post("/{workflow_id}/publish", response_model=WorkflowVersionOut)
async def publish_workflow(
    workspace_id: str, workflow_id: str, payload: PublishIn, db: DbSession, user: CurrentUser
) -> WorkflowVersion:
    await require_role(db, workspace_id, user.id, "editor")
    workflow = await get_workflow(db, workspace_id, workflow_id)
    publish_graph, subworkflow_references = await resolve_subworkflow_references(
        db,
        workspace_id,
        workflow.draft_graph,
        published=True,
        ancestors=(workflow.id,),
    )
    validate_graph(publish_graph)
    scripts = list(
        (
            await db.scalars(
                select(Script).where(
                    Script.workspace_id == workspace_id, Script.deleted_at.is_(None)
                )
            )
        ).all()
    )
    latest: dict[str, tuple[str, int]] = {}
    for script in scripts:
        version = await db.scalar(
            select(ScriptVersion).where(
                ScriptVersion.script_id == script.id, ScriptVersion.version == script.latest_version
            )
        )
        if version:
            latest[script.id] = (version.id, version.version)
    references = resolve_script_references(publish_graph, latest)
    if subworkflow_references:
        references["_subworkflows"] = subworkflow_references
    next_version = (
        await db.scalar(
            select(func.max(WorkflowVersion.version)).where(
                WorkflowVersion.workflow_id == workflow.id
            )
        )
        or 0
    ) + 1
    version = WorkflowVersion(
        workspace_id=workspace_id,
        workflow_id=workflow.id,
        version=next_version,
        graph=publish_graph,
        resolved_references=references,
        change_note=payload.change_note,
        created_by=user.id,
    )
    db.add(version)
    await db.flush()
    workflow.published_version_id = version.id
    workflow.published_access = payload.access
    db.add(
        audit(
            workspace_id,
            user.id,
            "workflow.published",
            "workflow",
            workflow.id,
            {"version": next_version, "access": payload.access},
        )
    )
    await db.commit()
    await db.refresh(version)
    return version


@router.get("/{workflow_id}/versions", response_model=list[WorkflowVersionOut])
async def list_versions(
    workspace_id: str, workflow_id: str, db: DbSession, user: CurrentUser
) -> list[WorkflowVersion]:
    await require_role(db, workspace_id, user.id)
    await get_workflow(db, workspace_id, workflow_id)
    return list(
        (
            await db.scalars(
                select(WorkflowVersion)
                .where(WorkflowVersion.workflow_id == workflow_id)
                .order_by(WorkflowVersion.version.desc())
            )
        ).all()
    )


@router.post("/{workflow_id}/versions/{version_id}/restore", response_model=WorkflowOut)
async def restore_version_to_draft(
    workspace_id: str,
    workflow_id: str,
    version_id: str,
    db: DbSession,
    user: CurrentUser,
) -> Workflow:
    await require_role(db, workspace_id, user.id, "editor")
    workflow = await get_workflow(db, workspace_id, workflow_id)
    version = await db.get(WorkflowVersion, version_id)
    if not version or version.workspace_id != workspace_id or version.workflow_id != workflow_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Workflow version not found")
    restored_graph = deepcopy(version.graph)
    validate_graph(restored_graph)
    workflow.draft_graph = restored_graph
    workflow.draft_version += 1
    db.add(
        audit(
            workspace_id,
            user.id,
            "workflow.version_restored",
            "workflow",
            workflow.id,
            {"version_id": version.id, "version": version.version},
        )
    )
    await db.commit()
    await db.refresh(workflow)
    return workflow


@router.post("/{workflow_id}/run", response_model=RunOut)
async def run_draft(
    workspace_id: str, workflow_id: str, payload: RunIn, db: DbSession, user: CurrentUser
) -> WorkflowRun:
    await require_role(db, workspace_id, user.id)
    workflow = await get_workflow(db, workspace_id, workflow_id)
    run = WorkflowRun(
        workspace_id=workspace_id,
        workflow_id=workflow_id,
        status="running",
        inputs=payload.inputs,
        created_by=user.id,
    )
    db.add(run)
    await db.flush()
    execution_graph, _ = await resolve_subworkflow_references(
        db,
        workspace_id,
        workflow.draft_graph,
        published=False,
        ancestors=(workflow.id,),
    )
    environment = await load_workflow_environment(db, workspace_id, workflow_id)
    model_providers = await load_model_provider_runtimes(db, workspace_id)
    system = build_system_variables(workflow_id=workflow_id, run_id=run.id, user_id=user.id)
    try:
        outputs, trace = execute_graph(
            execution_graph,
            payload.inputs,
            environment=environment,
            system=system,
            model_providers=model_providers,
        )
        run.status = "succeeded"
        run.outputs = outputs
        run.trace = trace
        run.finished_at = datetime.now(UTC)
    except WorkflowPause as pause:
        await set_run_waiting(db, run, execution_graph, pause)
    except Exception as exc:
        run.status = "failed"
        run.error = str(exc)
        run.finished_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(run)
    return run


@router.get("/{workflow_id}/approvals", response_model=list[ApprovalOut])
async def list_approvals(
    workspace_id: str,
    workflow_id: str,
    db: DbSession,
    user: CurrentUser,
) -> list[WorkflowApproval]:
    await require_role(db, workspace_id, user.id)
    await get_workflow(db, workspace_id, workflow_id)
    return list(
        (
            await db.scalars(
                select(WorkflowApproval)
                .where(
                    WorkflowApproval.workspace_id == workspace_id,
                    WorkflowApproval.workflow_id == workflow_id,
                )
                .order_by(WorkflowApproval.created_at.desc())
                .limit(100)
            )
        ).all()
    )


@router.post(
    "/{workflow_id}/runs/{run_id}/approvals/{approval_id}/respond",
    response_model=RunOut,
)
async def respond_to_approval(
    workspace_id: str,
    workflow_id: str,
    run_id: str,
    approval_id: str,
    payload: ApprovalResponseIn,
    db: DbSession,
    user: CurrentUser,
) -> WorkflowRun:
    await require_role(db, workspace_id, user.id)
    await get_workflow(db, workspace_id, workflow_id)
    run = await db.get(WorkflowRun, run_id)
    approval = await db.get(WorkflowApproval, approval_id)
    if (
        not run
        or run.workspace_id != workspace_id
        or run.workflow_id != workflow_id
        or not approval
        or approval.workspace_id != workspace_id
        or approval.workflow_id != workflow_id
        or approval.run_id != run_id
    ):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Approval not found")
    if approval.status != "pending" or run.status != "waiting":
        raise HTTPException(status.HTTP_409_CONFLICT, "Approval is no longer pending")
    now = datetime.now(UTC)
    expires_at = approval.expires_at
    if expires_at and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    if expires_at and expires_at < now:
        approval.status = "expired"
        run.status = "failed"
        run.error = "Human approval expired"
        run.finished_at = now
        await db.commit()
        raise HTTPException(status.HTTP_409_CONFLICT, "Approval has expired")
    actions = approval.request.get("actions", [])
    action = next((item for item in actions if str(item.get("id")) == payload.action_id), None)
    if not action:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Unknown approval action")
    response = {
        "action_id": payload.action_id,
        "action_value": action.get("value", payload.action_id),
        "data": payload.data,
        "comment": payload.comment,
        "responded_by": user.id,
    }
    approval.status = "responded"
    approval.response = response
    approval.responded_by = user.id
    approval.responded_at = now
    resume_state = deepcopy(approval.resume_state)
    resume_context = resume_state.setdefault("context", {})
    response_node_id = str(approval.request.get("_response_node_id") or approval.node_id)
    resume_context.setdefault("__human_responses__", {})[response_node_id] = response
    run.status = "running"
    run.error = None
    try:
        environment = await load_workflow_environment(db, workspace_id, workflow_id)
        model_providers = await load_model_provider_runtimes(db, workspace_id)
        system = build_system_variables(workflow_id=workflow_id, run_id=run.id, user_id=user.id)
        outputs, trace = execute_graph(
            approval.graph,
            run.inputs,
            resume_state=resume_state,
            environment=environment,
            system=system,
            model_providers=model_providers,
        )
        run.status = "succeeded"
        run.outputs = outputs
        run.trace = trace
        run.finished_at = datetime.now(UTC)
    except WorkflowPause as pause:
        await set_run_waiting(db, run, approval.graph, pause)
    except Exception as exc:
        run.status = "failed"
        run.error = str(exc)
        run.finished_at = datetime.now(UTC)
    db.add(audit(workspace_id, user.id, "workflow.approval_responded", "workflow_run", run.id, {"approval_id": approval.id, "action_id": payload.action_id}))
    await db.commit()
    await db.refresh(run)
    return run


@router.post("/{workflow_id}/nodes/{node_id}/run", response_model=RunOut)
async def run_draft_node(
    workspace_id: str,
    workflow_id: str,
    node_id: str,
    payload: RunIn,
    db: DbSession,
    user: CurrentUser,
) -> WorkflowRun:
    await require_role(db, workspace_id, user.id)
    workflow = await get_workflow(db, workspace_id, workflow_id)
    execution_graph, _ = await resolve_subworkflow_references(
        db,
        workspace_id,
        workflow.draft_graph,
        published=False,
        ancestors=(workflow.id,),
    )
    node = next((item for item in execution_graph.get("nodes", []) if item.get("id") == node_id), None)
    if not node:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Workflow node not found")
    validate_run_inputs(execution_graph, payload.inputs)
    run = WorkflowRun(
        workspace_id=workspace_id,
        workflow_id=workflow_id,
        status="running",
        triggered_by="node",
        inputs=payload.inputs,
        created_by=user.id,
    )
    db.add(run)
    await db.flush()
    try:
        environment = await load_workflow_environment(db, workspace_id, workflow_id)
        model_providers = await load_model_provider_runtimes(db, workspace_id)
        system = build_system_variables(workflow_id=workflow_id, run_id=run.id, user_id=user.id)
        output, trace = execute_node_preview(
            node,
            payload.inputs,
            environment=environment,
            system=system,
            model_providers=model_providers,
        )
        run.status = "succeeded"
        run.outputs = output if isinstance(output, dict) else {"value": output}
        run.trace = [trace]
    except Exception as exc:
        run.status = "failed"
        run.error = str(exc)
    run.finished_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(run)
    return run


@router.get("/{workflow_id}/runs", response_model=list[RunOut])
async def list_runs(
    workspace_id: str, workflow_id: str, db: DbSession, user: CurrentUser
) -> list[WorkflowRun]:
    await require_role(db, workspace_id, user.id)
    await get_workflow(db, workspace_id, workflow_id)
    return list(
        (
            await db.scalars(
                select(WorkflowRun)
                .where(
                    WorkflowRun.workspace_id == workspace_id,
                    WorkflowRun.workflow_id == workflow_id,
                )
                .order_by(WorkflowRun.created_at.desc())
                .limit(100)
            )
        ).all()
    )
