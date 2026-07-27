from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.core.security import decrypt_secret, encrypt_secret
from app.models.entities import ModelProvider
from app.schemas.common import ApiModel, MessageOut
from app.services.workspaces import audit, require_role

router = APIRouter(prefix="/workspaces/{workspace_id}/models", tags=["models"])


class ModelCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    provider_type: str = "openai-compatible"
    base_url: str
    api_key: str
    default_model: str
    config: dict[str, Any] = {}


class ModelOut(ApiModel):
    id: str
    workspace_id: str
    name: str
    provider_type: str
    base_url: str
    default_model: str
    config: dict[str, Any]
    has_api_key: bool = True


@router.get("", response_model=list[ModelOut])
async def list_models(workspace_id: str, db: DbSession, user: CurrentUser) -> list[ModelOut]:
    await require_role(db, workspace_id, user.id)
    items = (
        await db.scalars(select(ModelProvider).where(ModelProvider.workspace_id == workspace_id))
    ).all()
    return [ModelOut.model_validate(item) for item in items]


@router.post("", response_model=ModelOut, status_code=status.HTTP_201_CREATED)
async def create_model(
    workspace_id: str, payload: ModelCreate, db: DbSession, user: CurrentUser
) -> ModelProvider:
    await require_role(db, workspace_id, user.id, "admin")
    model = ModelProvider(
        workspace_id=workspace_id,
        name=payload.name,
        provider_type=payload.provider_type,
        base_url=payload.base_url.rstrip("/"),
        encrypted_api_key=encrypt_secret(payload.api_key),
        default_model=payload.default_model,
        config=payload.config,
        created_by=user.id,
    )
    db.add(model)
    await db.flush()
    db.add(audit(workspace_id, user.id, "model.created", "model", model.id))
    await db.commit()
    await db.refresh(model)
    return model


@router.post("/{model_id}/test", response_model=MessageOut)
async def test_model(
    workspace_id: str, model_id: str, db: DbSession, user: CurrentUser
) -> MessageOut:
    await require_role(db, workspace_id, user.id, "admin")
    model = await db.get(ModelProvider, model_id)
    if not model or model.workspace_id != workspace_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Model provider not found")
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(
                f"{model.base_url}/models",
                headers={"Authorization": f"Bearer {decrypt_secret(model.encrypted_api_key)}"},
            )
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"Model connection failed: {exc}") from exc
    return MessageOut(message="Model provider connected")


@router.delete("/{model_id}", response_model=MessageOut)
async def delete_model(
    workspace_id: str, model_id: str, db: DbSession, user: CurrentUser
) -> MessageOut:
    await require_role(db, workspace_id, user.id, "admin")
    model = await db.get(ModelProvider, model_id)
    if not model or model.workspace_id != workspace_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Model provider not found")
    await db.delete(model)
    db.add(audit(workspace_id, user.id, "model.deleted", "model", model_id))
    await db.commit()
    return MessageOut(message="Model provider deleted")
