import json

import httpx
from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from starlette.concurrency import run_in_threadpool

from app.api.deps import CurrentUser, DbSession
from app.core.config import get_settings
from app.models.entities import Dataset, KnowledgeChunk, KnowledgeDocument, StoredFile
from app.schemas.common import ApiModel, MessageOut
from app.services.storage import put, remove
from app.services.workspaces import audit, require_role

router = APIRouter(prefix="/workspaces/{workspace_id}/knowledge", tags=["knowledge"])


class DatasetCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = ""


class DatasetOut(ApiModel):
    id: str
    workspace_id: str
    name: str
    description: str


class DocumentOut(ApiModel):
    id: str
    dataset_id: str
    name: str
    status: str
    metadata_json: dict
    error: str | None


async def get_dataset(db: DbSession, workspace_id: str, dataset_id: str) -> Dataset:
    dataset = await db.get(Dataset, dataset_id)
    if not dataset or dataset.workspace_id != workspace_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Knowledge base not found")
    return dataset


@router.get("", response_model=list[DatasetOut])
async def list_datasets(workspace_id: str, db: DbSession, user: CurrentUser) -> list[Dataset]:
    await require_role(db, workspace_id, user.id)
    return list(
        (await db.scalars(select(Dataset).where(Dataset.workspace_id == workspace_id))).all()
    )


@router.post("", response_model=DatasetOut, status_code=status.HTTP_201_CREATED)
async def create_dataset(
    workspace_id: str, payload: DatasetCreate, db: DbSession, user: CurrentUser
) -> Dataset:
    await require_role(db, workspace_id, user.id, "editor")
    item = Dataset(
        workspace_id=workspace_id,
        name=payload.name,
        description=payload.description,
        created_by=user.id,
    )
    db.add(item)
    await db.flush()
    db.add(audit(workspace_id, user.id, "dataset.created", "dataset", item.id))
    await db.commit()
    await db.refresh(item)
    return item


@router.post(
    "/{dataset_id}/documents", response_model=DocumentOut, status_code=status.HTTP_201_CREATED
)
async def upload_document(
    workspace_id: str,
    dataset_id: str,
    db: DbSession,
    user: CurrentUser,
    file: UploadFile = File(...),
    metadata: str = Form("{}"),
) -> KnowledgeDocument:
    await require_role(db, workspace_id, user.id, "editor")
    await get_dataset(db, workspace_id, dataset_id)
    content = await file.read()
    if len(content) > get_settings().max_upload_bytes:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "File too large")
    key, digest = await run_in_threadpool(
        put,
        workspace_id,
        file.filename or "document",
        file.content_type or "application/octet-stream",
        content,
    )
    stored = StoredFile(
        workspace_id=workspace_id,
        object_key=key,
        filename=file.filename or "document",
        content_type=file.content_type or "application/octet-stream",
        size=len(content),
        sha256=digest,
        created_by=user.id,
    )
    db.add(stored)
    await db.flush()
    document = KnowledgeDocument(
        workspace_id=workspace_id,
        dataset_id=dataset_id,
        stored_file_id=stored.id,
        name=stored.filename,
        metadata_json=json.loads(metadata),
        created_by=user.id,
    )
    db.add(document)
    await db.flush()
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                f"{get_settings().document_worker_url}/inspect",
                files={"file": (stored.filename, content, stored.content_type)},
            )
            response.raise_for_status()
            extracted = response.json()
        document.extracted_content = extracted
        document.status = "ready"
        text = json.dumps(extracted, ensure_ascii=False)
        for ordinal, offset in enumerate(range(0, len(text), 1000)):
            db.add(
                KnowledgeChunk(
                    workspace_id=workspace_id,
                    dataset_id=dataset_id,
                    document_id=document.id,
                    ordinal=ordinal,
                    content=text[offset : offset + 1200],
                    metadata_json=document.metadata_json,
                )
            )
    except Exception as exc:
        document.status = "failed"
        document.error = str(exc)
    db.add(audit(workspace_id, user.id, "document.uploaded", "document", document.id))
    await db.commit()
    await db.refresh(document)
    return document


@router.get("/{dataset_id}/documents", response_model=list[DocumentOut])
async def list_documents(
    workspace_id: str, dataset_id: str, db: DbSession, user: CurrentUser
) -> list[KnowledgeDocument]:
    await require_role(db, workspace_id, user.id)
    await get_dataset(db, workspace_id, dataset_id)
    return list(
        (
            await db.scalars(
                select(KnowledgeDocument)
                .where(
                    KnowledgeDocument.workspace_id == workspace_id,
                    KnowledgeDocument.dataset_id == dataset_id,
                )
                .order_by(KnowledgeDocument.created_at.desc())
            )
        ).all()
    )


@router.delete("/{dataset_id}/documents/{document_id}", response_model=MessageOut)
async def delete_document(
    workspace_id: str,
    dataset_id: str,
    document_id: str,
    db: DbSession,
    user: CurrentUser,
) -> MessageOut:
    await require_role(db, workspace_id, user.id, "editor")
    await get_dataset(db, workspace_id, dataset_id)
    document = await db.get(KnowledgeDocument, document_id)
    if not document or document.workspace_id != workspace_id or document.dataset_id != dataset_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
    stored = await db.get(StoredFile, document.stored_file_id)
    await db.execute(delete(KnowledgeChunk).where(KnowledgeChunk.document_id == document_id))
    await db.delete(document)
    if stored:
        await db.delete(stored)
    db.add(audit(workspace_id, user.id, "document.deleted", "document", document_id))
    await db.commit()
    if stored:
        try:
            await run_in_threadpool(remove, stored.object_key)
        except Exception:
            pass
    return MessageOut(message="Document deleted")


@router.delete("/{dataset_id}", response_model=MessageOut)
async def delete_dataset(
    workspace_id: str, dataset_id: str, db: DbSession, user: CurrentUser
) -> MessageOut:
    await require_role(db, workspace_id, user.id, "editor")
    dataset = await get_dataset(db, workspace_id, dataset_id)
    documents = list(
        (
            await db.scalars(
                select(KnowledgeDocument).where(
                    KnowledgeDocument.workspace_id == workspace_id,
                    KnowledgeDocument.dataset_id == dataset_id,
                )
            )
        ).all()
    )
    stored_ids = [item.stored_file_id for item in documents]
    stored_files = list(
        (await db.scalars(select(StoredFile).where(StoredFile.id.in_(stored_ids)))).all()
    ) if stored_ids else []
    await db.execute(delete(KnowledgeChunk).where(KnowledgeChunk.dataset_id == dataset_id))
    await db.execute(delete(KnowledgeDocument).where(KnowledgeDocument.dataset_id == dataset_id))
    for stored in stored_files:
        await db.delete(stored)
    await db.delete(dataset)
    db.add(audit(workspace_id, user.id, "dataset.deleted", "dataset", dataset_id))
    await db.commit()
    for stored in stored_files:
        try:
            await run_in_threadpool(remove, stored.object_key)
        except Exception:
            pass
    return MessageOut(message="Knowledge base deleted")
