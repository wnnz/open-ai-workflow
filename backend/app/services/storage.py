import hashlib
import io
import secrets
from pathlib import Path, PurePosixPath
from typing import BinaryIO

from app.core.config import get_settings

CHUNK_SIZE = 1024 * 1024


def storage_root() -> Path:
    root = Path(get_settings().storage_path).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def object_path(object_key: str) -> Path:
    key = PurePosixPath(object_key)
    if key.is_absolute() or not key.parts or any(part in {"", ".", ".."} for part in key.parts):
        raise ValueError("Invalid object key")
    root = storage_root()
    destination = root.joinpath(*key.parts).resolve()
    if not destination.is_relative_to(root):
        raise ValueError("Invalid object key")
    return destination


def create_object_key(workspace_id: str, filename: str) -> str:
    safe_name = filename.replace("/", "_").replace("\\", "_") or "file"
    return f"workspaces/{workspace_id}/{secrets.token_hex(12)}/{safe_name}"


def put(workspace_id: str, filename: str, content_type: str, content: bytes) -> tuple[str, str]:
    return put_stream(workspace_id, filename, content_type, io.BytesIO(content), len(content))


def put_stream(
    workspace_id: str,
    filename: str,
    content_type: str,
    stream: BinaryIO,
    size: int,
) -> tuple[str, str]:
    del content_type
    key = create_object_key(workspace_id, filename)
    destination = object_path(key)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.{secrets.token_hex(8)}.part")
    digest = hashlib.sha256()
    written = 0
    try:
        with temporary.open("xb") as target:
            while chunk := stream.read(CHUNK_SIZE):
                target.write(chunk)
                digest.update(chunk)
                written += len(chunk)
        if written != size:
            raise ValueError(f"Upload size mismatch: expected {size}, received {written}")
        temporary.replace(destination)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    return key, digest.hexdigest()


def remove(object_key: str) -> None:
    object_path(object_key).unlink(missing_ok=True)
