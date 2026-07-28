import io
import zipfile
from datetime import UTC, datetime

import httpx
from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.core.config import get_settings
from app.models.entities import Script, ScriptVersion
from app.schemas.common import MessageOut
from app.schemas.script import (
    ScriptCreate,
    ScriptOut,
    ScriptTestIn,
    ScriptTestOut,
    ScriptUpdate,
    ScriptVersionOut,
)
from app.services.scripts import validate_inputs, validate_script
from app.services.workspaces import audit, require_role, slugify

router = APIRouter(prefix="/workspaces/{workspace_id}/scripts", tags=["scripts"])


async def get_script(db: DbSession, workspace_id: str, script_id: str) -> Script:
    script = await db.get(Script, script_id)
    if not script or script.workspace_id != workspace_id or script.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Script not found")
    return script


@router.get("", response_model=list[ScriptOut])
async def list_scripts(
    workspace_id: str, db: DbSession, user: CurrentUser, q: str | None = None
) -> list[Script]:
    await require_role(db, workspace_id, user.id)
    query = select(Script).where(Script.workspace_id == workspace_id, Script.deleted_at.is_(None))
    if q:
        query = query.where(Script.name.ilike(f"%{q}%"))
    return list((await db.scalars(query.order_by(Script.updated_at.desc()))).all())


@router.post("", response_model=ScriptOut, status_code=status.HTTP_201_CREATED)
async def create_script(
    workspace_id: str, payload: ScriptCreate, db: DbSession, user: CurrentUser
) -> Script:
    await require_role(db, workspace_id, user.id, "editor")
    digest = validate_script(
        payload.source_code, payload.entrypoint, payload.input_schema, payload.output_schema
    )
    script = Script(
        workspace_id=workspace_id,
        name=payload.name,
        slug=payload.slug or slugify(payload.name),
        description=payload.description,
        tags=payload.tags,
        latest_version=1,
        created_by=user.id,
    )
    db.add(script)
    await db.flush()
    db.add(
        ScriptVersion(
            workspace_id=workspace_id,
            script_id=script.id,
            version=1,
            source_code=payload.source_code,
            entrypoint=payload.entrypoint,
            input_schema=payload.input_schema,
            output_schema=payload.output_schema,
            content_hash=digest,
            change_note=payload.change_note,
            created_by=user.id,
        )
    )
    db.add(audit(workspace_id, user.id, "script.created", "script", script.id))
    await db.commit()
    await db.refresh(script)
    return script


@router.post("/upload", response_model=ScriptOut, status_code=status.HTTP_201_CREATED)
async def upload_script(
    workspace_id: str,
    db: DbSession,
    user: CurrentUser,
    file: UploadFile = File(...),
    name: str = Form(...),
    entrypoint: str = Form("main"),
) -> Script:
    await require_role(db, workspace_id, user.id, "editor")
    content = await file.read()
    if len(content) > get_settings().max_upload_bytes:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "File too large")
    filename = (file.filename or "").lower()
    if filename.endswith(".py"):
        source = content.decode("utf-8")
        source_type = "python"
    elif filename.endswith(".zip"):
        try:
            archive = zipfile.ZipFile(io.BytesIO(content))
            unsafe = [
                item
                for item in archive.infolist()
                if item.filename.startswith(("/", "\\")) or ".." in item.filename.split("/")
            ]
            if unsafe:
                raise ValueError("Unsafe archive path")
            module = (
                entrypoint.split(":", 1)[0].replace(".", "/") + ".py"
                if ":" in entrypoint
                else "main.py"
            )
            source = archive.read(module).decode("utf-8")
            source_type = "zip"
        except (KeyError, ValueError, zipfile.BadZipFile, UnicodeDecodeError) as exc:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT, f"Invalid script archive: {exc}"
            ) from exc
    else:
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "Only .py and .zip are supported"
        )
    function_name = entrypoint.split(":")[-1]
    digest = validate_script(source, function_name, {"type": "object"}, {})
    script = Script(
        workspace_id=workspace_id,
        name=name,
        slug=slugify(name),
        latest_version=1,
        created_by=user.id,
    )
    db.add(script)
    await db.flush()
    db.add(
        ScriptVersion(
            workspace_id=workspace_id,
            script_id=script.id,
            version=1,
            source_type=source_type,
            source_code=source,
            entrypoint=entrypoint,
            input_schema={"type": "object"},
            output_schema={},
            content_hash=digest,
            change_note=f"Uploaded {file.filename}",
            created_by=user.id,
        )
    )
    db.add(
        audit(
            workspace_id,
            user.id,
            "script.uploaded",
            "script",
            script.id,
            {"filename": file.filename},
        )
    )
    await db.commit()
    await db.refresh(script)
    return script


@router.get("/{script_id}", response_model=ScriptOut)
async def read_script(
    workspace_id: str, script_id: str, db: DbSession, user: CurrentUser
) -> Script:
    await require_role(db, workspace_id, user.id)
    return await get_script(db, workspace_id, script_id)


@router.get("/{script_id}/versions", response_model=list[ScriptVersionOut])
async def list_versions(
    workspace_id: str, script_id: str, db: DbSession, user: CurrentUser
) -> list[ScriptVersion]:
    await require_role(db, workspace_id, user.id)
    await get_script(db, workspace_id, script_id)
    return list(
        (
            await db.scalars(
                select(ScriptVersion)
                .where(
                    ScriptVersion.script_id == script_id, ScriptVersion.workspace_id == workspace_id
                )
                .order_by(ScriptVersion.version.desc())
            )
        ).all()
    )


@router.put("/{script_id}", response_model=ScriptOut)
async def update_script(
    workspace_id: str, script_id: str, payload: ScriptUpdate, db: DbSession, user: CurrentUser
) -> Script:
    await require_role(db, workspace_id, user.id, "editor")
    script = await get_script(db, workspace_id, script_id)
    if script.latest_version != payload.expected_version:
        raise HTTPException(status.HTTP_409_CONFLICT, "Script was updated by another member")
    digest = validate_script(
        payload.source_code, payload.entrypoint, payload.input_schema, payload.output_schema
    )
    script.latest_version += 1
    if payload.name is not None:
        script.name = payload.name
    if payload.description is not None:
        script.description = payload.description
    if payload.tags is not None:
        script.tags = payload.tags
    db.add(
        ScriptVersion(
            workspace_id=workspace_id,
            script_id=script.id,
            version=script.latest_version,
            source_code=payload.source_code,
            entrypoint=payload.entrypoint,
            input_schema=payload.input_schema,
            output_schema=payload.output_schema,
            content_hash=digest,
            change_note=payload.change_note,
            created_by=user.id,
        )
    )
    db.add(
        audit(
            workspace_id,
            user.id,
            "script.version_created",
            "script",
            script.id,
            {"version": script.latest_version},
        )
    )
    await db.commit()
    await db.refresh(script)
    return script


@router.post("/{script_id}/test", response_model=ScriptTestOut)
async def test_script(
    workspace_id: str, script_id: str, payload: ScriptTestIn, db: DbSession, user: CurrentUser
) -> ScriptTestOut:
    await require_role(db, workspace_id, user.id, "editor")
    script = await get_script(db, workspace_id, script_id)
    version_number = payload.version or script.latest_version
    version = await db.scalar(
        select(ScriptVersion).where(
            ScriptVersion.script_id == script_id, ScriptVersion.version == version_number
        )
    )
    if not version:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Script version not found")
    validate_inputs(version.input_schema, payload.inputs)
    try:
        async with httpx.AsyncClient(timeout=payload.timeout_seconds + 5) as client:
            response = await client.post(
                f"{get_settings().sandbox_url}/execute",
                json={
                    "source": version.source_code,
                    "entrypoint": version.entrypoint.split(":")[-1],
                    "inputs": payload.inputs,
                    "timeout_seconds": payload.timeout_seconds,
                },
                headers={"X-Sandbox-Token": get_settings().app_secret_key},
            )
            response.raise_for_status()
            return ScriptTestOut.model_validate(response.json())
    except httpx.HTTPError as exc:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, f"Sandbox unavailable: {exc}"
        ) from exc


@router.delete("/{script_id}", response_model=MessageOut)
async def delete_script(
    workspace_id: str, script_id: str, db: DbSession, user: CurrentUser
) -> MessageOut:
    await require_role(db, workspace_id, user.id, "editor")
    script = await get_script(db, workspace_id, script_id)
    script.deleted_at = datetime.now(UTC)
    db.add(audit(workspace_id, user.id, "script.deleted", "script", script.id))
    await db.commit()
    return MessageOut(message="Script deleted; referenced versions are retained")
