from __future__ import annotations

import hashlib
from collections.abc import Callable
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import StoredFile
from app.services.document_processing import GeneratedFile
from app.services.storage import put

INTERNAL_FILE_KEY = "__ordo_object_key"


def _file_ids(value: Any) -> set[str]:
    ids: set[str] = set()
    if isinstance(value, dict):
        if value.get("id") and value.get("filename") and value.get("content_type"):
            ids.add(str(value["id"]))
        for item in value.values():
            ids.update(_file_ids(item))
    elif isinstance(value, list):
        for item in value:
            ids.update(_file_ids(item))
    return ids


async def hydrate_file_references(
    db: AsyncSession, workspace_id: str, value: dict[str, Any]
) -> dict[str, Any]:
    ids = _file_ids(value)
    if not ids:
        return value
    files = list(
        (
            await db.scalars(
                select(StoredFile).where(
                    StoredFile.workspace_id == workspace_id,
                    StoredFile.id.in_(ids),
                )
            )
        ).all()
    )
    by_id = {item.id: item for item in files}
    if missing := ids - set(by_id):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            f"Uploaded file is missing or belongs to another workspace: {sorted(missing)[0]}",
        )

    def visit(item: Any) -> Any:
        if isinstance(item, dict):
            result = {key: visit(entry) for key, entry in item.items()}
            stored = by_id.get(str(item.get("id") or ""))
            if stored and item.get("filename") and item.get("content_type"):
                result[INTERNAL_FILE_KEY] = stored.object_key
            return result
        if isinstance(item, list):
            return [visit(entry) for entry in item]
        return item

    return visit(value)


def strip_internal_file_metadata(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: strip_internal_file_metadata(item)
            for key, item in value.items()
            if not str(key).startswith("__ordo_")
        }
    if isinstance(value, list):
        return [strip_internal_file_metadata(item) for item in value]
    return value


async def materialize_generated_files(
    db: AsyncSession,
    *,
    workspace_id: str,
    created_by: str,
    outputs: dict[str, Any],
    trace: list[dict[str, Any]],
    download_url: Callable[[str], str],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    descriptors: dict[tuple[str, str], dict[str, Any]] = {}

    async def visit(item: Any) -> Any:
        if isinstance(item, GeneratedFile):
            digest = hashlib.sha256(item.content).hexdigest()
            cache_key = (digest, item.filename)
            if cache_key not in descriptors:
                object_key, stored_digest = put(
                    workspace_id,
                    item.filename,
                    item.content_type,
                    item.content,
                )
                stored = StoredFile(
                    workspace_id=workspace_id,
                    object_key=object_key,
                    filename=item.filename,
                    content_type=item.content_type,
                    size=len(item.content),
                    sha256=stored_digest,
                    created_by=created_by,
                )
                db.add(stored)
                await db.flush()
                descriptors[cache_key] = {
                    "id": stored.id,
                    "filename": stored.filename,
                    "content_type": stored.content_type,
                    "size": stored.size,
                    "download_url": download_url(stored.id),
                }
            return descriptors[cache_key]
        if isinstance(item, dict):
            return {
                key: await visit(value)
                for key, value in item.items()
                if not str(key).startswith("__ordo_")
            }
        if isinstance(item, list):
            return [await visit(value) for value in item]
        return item

    materialized = await visit({"outputs": outputs, "trace": trace})
    return materialized["outputs"], materialized["trace"]


def contains_file_id(value: Any, file_id: str) -> bool:
    if isinstance(value, dict):
        if str(value.get("id") or "") == file_id and value.get("download_url"):
            return True
        return any(contains_file_id(item, file_id) for item in value.values())
    if isinstance(value, list):
        return any(contains_file_id(item, file_id) for item in value)
    return False
