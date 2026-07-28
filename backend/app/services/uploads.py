from fastapi import HTTPException, UploadFile, status
from starlette.concurrency import run_in_threadpool

from app.services.storage import put_stream


async def store_upload(
    workspace_id: str,
    file: UploadFile,
    max_bytes: int,
) -> tuple[str, str, int]:
    size = file.size
    if size is None:
        await run_in_threadpool(file.file.seek, 0, 2)
        size = await run_in_threadpool(file.file.tell)
    if size > max_bytes:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "File too large")
    await run_in_threadpool(file.file.seek, 0)
    key, digest = await run_in_threadpool(
        put_stream,
        workspace_id,
        file.filename or "file",
        file.content_type or "application/octet-stream",
        file.file,
        size,
    )
    return key, digest, size
