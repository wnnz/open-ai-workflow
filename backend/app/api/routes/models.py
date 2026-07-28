from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Body, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.deps import CurrentUser, DbSession
from app.core.security import decrypt_secret, encrypt_secret
from app.models.entities import ModelProvider, Workflow, WorkflowVersion
from app.schemas.common import ApiModel, MessageOut
from app.services.model_providers import (
    fetch_provider_models,
    normalize_base_url,
    normalize_provider_config,
    test_provider_connection,
)
from app.services.workspaces import audit, require_role

router = APIRouter(prefix="/workspaces/{workspace_id}/models", tags=["models"])


class ModelCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    provider_type: str = Field(default="openai-compatible", max_length=40)
    base_url: str
    api_key: str = Field(default="", max_length=20_000)
    default_model: str = Field(min_length=1, max_length=120)
    config: dict[str, Any] = Field(default_factory=dict)

    @field_validator("name", "default_model")
    @classmethod
    def trim_required(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Value cannot be blank")
        return normalized

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, value: str) -> str:
        return normalize_base_url(value)

    @field_validator("config")
    @classmethod
    def validate_config(cls, value: dict[str, Any]) -> dict[str, Any]:
        return normalize_provider_config(value)


class ModelUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    provider_type: str | None = Field(default=None, max_length=40)
    base_url: str | None = None
    api_key: str | None = Field(default=None, max_length=20_000)
    default_model: str | None = Field(default=None, min_length=1, max_length=120)
    config: dict[str, Any] | None = None

    @field_validator("name", "default_model")
    @classmethod
    def trim_optional(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("Value cannot be blank")
        return normalized

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, value: str | None) -> str | None:
        return normalize_base_url(value) if value is not None else None

    @field_validator("config")
    @classmethod
    def validate_config(cls, value: dict[str, Any] | None) -> dict[str, Any] | None:
        return normalize_provider_config(value) if value is not None else None


class ConnectionTestOptions(BaseModel):
    verify_inference: bool = False


class ModelConnectionTest(ModelCreate):
    verify_inference: bool = False


class SavedModelConnectionTest(ModelUpdate):
    verify_inference: bool = False


class ConnectionTestOut(BaseModel):
    message: str
    status: str
    latency_ms: float
    models: list[str]
    default_model_available: bool | None
    inference_verified: bool
    warning: str = ""
    capabilities: dict[str, bool]


class ModelCatalogRequest(BaseModel):
    base_url: str
    api_key: str = Field(default="", max_length=20_000)
    config: dict[str, Any] = Field(default_factory=dict)

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, value: str) -> str:
        return normalize_base_url(value)

    @field_validator("config")
    @classmethod
    def validate_config(cls, value: dict[str, Any]) -> dict[str, Any]:
        return normalize_provider_config(value)


class SavedModelCatalogRequest(BaseModel):
    base_url: str | None = None
    api_key: str | None = Field(default=None, max_length=20_000)
    config: dict[str, Any] | None = None

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, value: str | None) -> str | None:
        return normalize_base_url(value) if value is not None else None

    @field_validator("config")
    @classmethod
    def validate_config(cls, value: dict[str, Any] | None) -> dict[str, Any] | None:
        return normalize_provider_config(value) if value is not None else None


class ModelCatalogOut(BaseModel):
    models: list[str]
    latency_ms: float


class ModelOut(ApiModel):
    id: str
    workspace_id: str
    name: str
    provider_type: str
    base_url: str
    default_model: str
    config: dict[str, Any]
    has_api_key: bool
    last_tested_at: str | None = None
    last_test_status: str = "untested"
    last_test_latency_ms: float | None = None
    available_models: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


def public_model(provider: ModelProvider) -> ModelOut:
    config = normalize_provider_config(provider.config)
    return ModelOut(
        id=provider.id,
        workspace_id=provider.workspace_id,
        name=provider.name,
        provider_type=provider.provider_type,
        base_url=provider.base_url,
        default_model=provider.default_model,
        config={
            key: value
            for key, value in config.items()
            if key not in {"last_tested_at", "last_test_status", "last_test_latency_ms", "available_models"}
        },
        has_api_key=bool(decrypt_secret(provider.encrypted_api_key)),
        last_tested_at=config.get("last_tested_at"),
        last_test_status=str(config.get("last_test_status", "untested")),
        last_test_latency_ms=config.get("last_test_latency_ms"),
        available_models=list(config.get("available_models", []))[:200],
        created_at=provider.created_at,
        updated_at=provider.updated_at,
    )


async def get_provider(db: DbSession, workspace_id: str, model_id: str) -> ModelProvider:
    provider = await db.get(ModelProvider, model_id)
    if not provider or provider.workspace_id != workspace_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Model provider not found")
    return provider


async def commit_provider(db: DbSession, duplicate_message: str) -> None:
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, duplicate_message) from exc


def graph_uses_provider(graph: dict[str, Any], provider_id: str) -> bool:
    return any(
        str(node.get("data", {}).get("config", {}).get("provider_id", "")) == provider_id
        for node in graph.get("nodes", [])
        if isinstance(node, dict)
    )


async def provider_references(
    db: DbSession, workspace_id: str, provider_id: str
) -> list[dict[str, Any]]:
    workflows = list(
        (
            await db.scalars(
                select(Workflow).where(
                    Workflow.workspace_id == workspace_id,
                    Workflow.deleted_at.is_(None),
                )
            )
        ).all()
    )
    workflow_ids = [workflow.id for workflow in workflows]
    versions = (
        list(
            (
                await db.scalars(
                    select(WorkflowVersion).where(
                        WorkflowVersion.workspace_id == workspace_id,
                        WorkflowVersion.workflow_id.in_(workflow_ids),
                    )
                )
            ).all()
        )
        if workflow_ids
        else []
    )
    by_workflow: dict[str, dict[str, Any]] = {}
    for workflow in workflows:
        if graph_uses_provider(workflow.draft_graph, provider_id):
            by_workflow[workflow.id] = {"id": workflow.id, "name": workflow.name, "scope": "draft"}
    workflow_names = {workflow.id: workflow.name for workflow in workflows}
    for version in versions:
        if graph_uses_provider(version.graph, provider_id):
            existing = by_workflow.get(version.workflow_id)
            scope = "draft_and_versions" if existing else "published_version"
            by_workflow[version.workflow_id] = {
                "id": version.workflow_id,
                "name": workflow_names.get(version.workflow_id, version.workflow_id),
                "scope": scope,
            }
    return sorted(by_workflow.values(), key=lambda item: str(item["name"]).casefold())


@router.get("", response_model=list[ModelOut])
async def list_models(workspace_id: str, db: DbSession, user: CurrentUser) -> list[ModelOut]:
    await require_role(db, workspace_id, user.id)
    items = (
        await db.scalars(
            select(ModelProvider)
            .where(ModelProvider.workspace_id == workspace_id)
            .order_by(ModelProvider.created_at, ModelProvider.name)
        )
    ).all()
    return [public_model(item) for item in items]


@router.post("/connection-test", response_model=ConnectionTestOut)
async def test_unsaved_model(
    workspace_id: str,
    payload: ModelConnectionTest,
    db: DbSession,
    user: CurrentUser,
) -> ConnectionTestOut:
    await require_role(db, workspace_id, user.id, "admin")
    result = await test_provider_connection(
        base_url=payload.base_url,
        api_key=payload.api_key,
        default_model=payload.default_model,
        config=payload.config,
        verify_inference=payload.verify_inference,
    )
    return ConnectionTestOut(**result)


@router.post("/catalog", response_model=ModelCatalogOut)
async def fetch_unsaved_model_catalog(
    workspace_id: str,
    payload: ModelCatalogRequest,
    db: DbSession,
    user: CurrentUser,
) -> ModelCatalogOut:
    await require_role(db, workspace_id, user.id, "admin")
    result = await fetch_provider_models(
        base_url=payload.base_url,
        api_key=payload.api_key,
        config=payload.config,
    )
    return ModelCatalogOut(**result)


@router.post("", response_model=ModelOut, status_code=status.HTTP_201_CREATED)
async def create_model(
    workspace_id: str, payload: ModelCreate, db: DbSession, user: CurrentUser
) -> ModelOut:
    await require_role(db, workspace_id, user.id, "admin")
    provider = ModelProvider(
        workspace_id=workspace_id,
        name=payload.name,
        provider_type=payload.provider_type,
        base_url=payload.base_url,
        encrypted_api_key=encrypt_secret(payload.api_key),
        default_model=payload.default_model,
        config=payload.config,
        created_by=user.id,
    )
    db.add(provider)
    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "A model provider with this name already exists",
        ) from exc
    db.add(audit(workspace_id, user.id, "model.created", "model", provider.id))
    await commit_provider(db, "A model provider with this name already exists")
    await db.refresh(provider)
    return public_model(provider)


@router.patch("/{model_id}", response_model=ModelOut)
async def update_model(
    workspace_id: str,
    model_id: str,
    payload: ModelUpdate,
    db: DbSession,
    user: CurrentUser,
) -> ModelOut:
    await require_role(db, workspace_id, user.id, "admin")
    provider = await get_provider(db, workspace_id, model_id)
    changed = payload.model_dump(exclude_unset=True)
    api_key = changed.pop("api_key", None)
    config = changed.pop("config", None)
    for field, value in changed.items():
        setattr(provider, field, value)
    if api_key is not None:
        provider.encrypted_api_key = encrypt_secret(api_key)
    if config is not None:
        provider.config = {
            **provider.config,
            **config,
        }
    db.add(
        audit(
            workspace_id,
            user.id,
            "model.updated",
            "model",
            provider.id,
            {"api_key_rotated": api_key is not None},
        )
    )
    await commit_provider(db, "A model provider with this name already exists")
    await db.refresh(provider)
    return public_model(provider)


@router.post("/{model_id}/connection-test", response_model=ConnectionTestOut)
async def test_model_edits(
    workspace_id: str,
    model_id: str,
    payload: SavedModelConnectionTest,
    db: DbSession,
    user: CurrentUser,
) -> ConnectionTestOut:
    await require_role(db, workspace_id, user.id, "admin")
    provider = await get_provider(db, workspace_id, model_id)
    result = await test_provider_connection(
        base_url=payload.base_url or provider.base_url,
        api_key=payload.api_key
        if payload.api_key not in {None, ""}
        else decrypt_secret(provider.encrypted_api_key),
        default_model=payload.default_model or provider.default_model,
        config={**provider.config, **(payload.config or {})},
        verify_inference=payload.verify_inference,
    )
    return ConnectionTestOut(**result)


@router.post("/{model_id}/catalog", response_model=ModelCatalogOut)
async def fetch_saved_model_catalog(
    workspace_id: str,
    model_id: str,
    payload: SavedModelCatalogRequest,
    db: DbSession,
    user: CurrentUser,
) -> ModelCatalogOut:
    await require_role(db, workspace_id, user.id, "admin")
    provider = await get_provider(db, workspace_id, model_id)
    result = await fetch_provider_models(
        base_url=payload.base_url or provider.base_url,
        api_key=payload.api_key
        if payload.api_key not in {None, ""}
        else decrypt_secret(provider.encrypted_api_key),
        config={**provider.config, **(payload.config or {})},
    )
    return ModelCatalogOut(**result)


@router.post("/{model_id}/test", response_model=ConnectionTestOut)
async def test_model(
    workspace_id: str,
    model_id: str,
    db: DbSession,
    user: CurrentUser,
    payload: ConnectionTestOptions | None = Body(default=None),
) -> ConnectionTestOut:
    await require_role(db, workspace_id, user.id, "admin")
    provider = await get_provider(db, workspace_id, model_id)
    options = payload or ConnectionTestOptions()
    tested_at = datetime.now(UTC).isoformat()
    try:
        result = await test_provider_connection(
            base_url=provider.base_url,
            api_key=decrypt_secret(provider.encrypted_api_key),
            default_model=provider.default_model,
            config=provider.config,
            verify_inference=options.verify_inference,
        )
    except HTTPException as exc:
        provider.config = {
            **provider.config,
            "last_tested_at": tested_at,
            "last_test_status": "failed",
            "last_test_latency_ms": None,
        }
        db.add(
            audit(
                workspace_id,
                user.id,
                "model.test_failed",
                "model",
                provider.id,
                {"detail": str(exc.detail)},
            )
        )
        await db.commit()
        raise
    provider.config = {
        **provider.config,
        "last_tested_at": tested_at,
        "last_test_status": result["status"],
        "last_test_latency_ms": result["latency_ms"],
        "available_models": result["models"],
    }
    db.add(
        audit(
            workspace_id,
            user.id,
            "model.test_succeeded",
            "model",
            provider.id,
            {"latency_ms": result["latency_ms"], "inference_verified": result["inference_verified"]},
        )
    )
    await db.commit()
    return ConnectionTestOut(**result)


@router.delete("/{model_id}", response_model=MessageOut)
async def delete_model(
    workspace_id: str, model_id: str, db: DbSession, user: CurrentUser
) -> MessageOut:
    await require_role(db, workspace_id, user.id, "admin")
    provider = await get_provider(db, workspace_id, model_id)
    references = await provider_references(db, workspace_id, model_id)
    if references:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            {
                "message": "Model provider is used by workflows",
                "references": references,
            },
        )
    await db.delete(provider)
    db.add(audit(workspace_id, user.id, "model.deleted", "model", model_id))
    await db.commit()
    return MessageOut(message="Model provider deleted")
