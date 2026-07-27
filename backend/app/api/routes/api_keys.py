from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.core.security import api_key_token
from app.models.entities import ApiKey, Workflow
from app.schemas.api_key import ApiKeyCreate, ApiKeyCreated, ApiKeyOut
from app.services.workspaces import audit, require_role

router = APIRouter(prefix="/workspaces/{workspace_id}/api-keys", tags=["API keys"])


@router.get("", response_model=list[ApiKeyOut])
async def list_api_keys(workspace_id: str, db: DbSession, user: CurrentUser) -> list[ApiKey]:
    await require_role(db, workspace_id, user.id, "admin")
    return list((await db.scalars(select(ApiKey).where(ApiKey.workspace_id == workspace_id).order_by(ApiKey.created_at.desc()))).all())


@router.post("", response_model=ApiKeyCreated, status_code=status.HTTP_201_CREATED)
async def create_api_key(workspace_id: str, payload: ApiKeyCreate, db: DbSession, user: CurrentUser) -> dict:
    await require_role(db, workspace_id, user.id, "admin")
    if payload.workflow_id:
        workflow = await db.get(Workflow, payload.workflow_id)
        if not workflow or workflow.workspace_id != workspace_id or workflow.deleted_at is not None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Workflow not found")
    raw, prefix, digest = api_key_token()
    item = ApiKey(workspace_id=workspace_id, workflow_id=payload.workflow_id, name=payload.name, key_prefix=prefix, key_hash=digest, created_by=user.id)
    db.add(item)
    await db.flush()
    db.add(audit(workspace_id, user.id, "api_key.created", "api_key", item.id, {"workflow_id": payload.workflow_id}))
    await db.commit()
    await db.refresh(item)
    data = ApiKeyOut.model_validate(item).model_dump()
    return {**data, "key": raw}


@router.delete("/{api_key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_api_key(workspace_id: str, api_key_id: str, db: DbSession, user: CurrentUser) -> None:
    await require_role(db, workspace_id, user.id, "admin")
    item = await db.get(ApiKey, api_key_id)
    if not item or item.workspace_id != workspace_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "API key not found")
    from datetime import UTC, datetime
    item.revoked_at = datetime.now(UTC)
    db.add(audit(workspace_id, user.id, "api_key.revoked", "api_key", item.id))
    await db.commit()
