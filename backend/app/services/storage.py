import hashlib
import io
import secrets
from datetime import timedelta
from typing import BinaryIO

from minio import Minio

from app.core.config import get_settings


def client() -> Minio:
    settings = get_settings()
    return Minio(
        settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.minio_secure,
    )


def ensure_bucket() -> None:
    settings = get_settings()
    storage = client()
    if not storage.bucket_exists(settings.minio_bucket):
        storage.make_bucket(settings.minio_bucket)


def put(workspace_id: str, filename: str, content_type: str, content: bytes) -> tuple[str, str]:
    settings = get_settings()
    ensure_bucket()
    safe_name = filename.replace("/", "_").replace("\\", "_")
    key = f"workspaces/{workspace_id}/{secrets.token_hex(12)}/{safe_name}"
    client().put_object(
        settings.minio_bucket, key, io.BytesIO(content), len(content), content_type=content_type
    )
    return key, hashlib.sha256(content).hexdigest()


class HashingReader:
    def __init__(self, stream: BinaryIO) -> None:
        self.stream = stream
        self.digest = hashlib.sha256()

    def read(self, size: int = -1) -> bytes:
        chunk = self.stream.read(size)
        if chunk:
            self.digest.update(chunk)
        return chunk


def put_stream(
    workspace_id: str,
    filename: str,
    content_type: str,
    stream: BinaryIO,
    size: int,
) -> tuple[str, str]:
    settings = get_settings()
    ensure_bucket()
    safe_name = filename.replace("/", "_").replace("\\", "_")
    key = f"workspaces/{workspace_id}/{secrets.token_hex(12)}/{safe_name}"
    hashing_stream = HashingReader(stream)
    client().put_object(
        settings.minio_bucket,
        key,
        hashing_stream,
        size,
        content_type=content_type,
    )
    return key, hashing_stream.digest.hexdigest()


def presigned_get(object_key: str) -> str:
    settings = get_settings()
    return client().presigned_get_object(
        settings.minio_bucket, object_key, expires=timedelta(minutes=15)
    )


def remove(object_key: str) -> None:
    settings = get_settings()
    client().remove_object(settings.minio_bucket, object_key)
