from __future__ import annotations

import mimetypes
from pathlib import Path, PurePosixPath
from typing import Any

from fastapi import HTTPException, status

from app.core.config import get_settings
from app.services.document_processing import GeneratedFile

ARTIFACT_PATH_KEY = "__ordo_artifact_path"
MAX_ARTIFACT_BYTES = 50 * 1024 * 1024


def artifact_root() -> Path:
    root = Path(get_settings().sandbox_artifact_path).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def _artifact_path(relative_path: str) -> Path:
    relative = PurePosixPath(relative_path)
    if relative.is_absolute() or not relative.parts or any(
        part in {"", ".", ".."} for part in relative.parts
    ):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "Sandbox returned an invalid file artifact",
        )
    root = artifact_root()
    path = root.joinpath(*relative.parts).resolve()
    if not path.is_relative_to(root):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "Sandbox returned an invalid file artifact",
        )
    return path


def _cleanup_parent(path: Path) -> None:
    root = artifact_root()
    parent = path.parent
    while parent != root and parent.is_relative_to(root):
        try:
            parent.rmdir()
        except OSError:
            break
        parent = parent.parent


def consume_sandbox_artifacts(value: Any) -> Any:
    if isinstance(value, dict) and value.get(ARTIFACT_PATH_KEY):
        path = _artifact_path(str(value[ARTIFACT_PATH_KEY]))
        try:
            if not path.is_file():
                raise HTTPException(
                    status.HTTP_503_SERVICE_UNAVAILABLE,
                    "Sandbox output file is unavailable",
                )
            size = path.stat().st_size
            if size > MAX_ARTIFACT_BYTES:
                raise HTTPException(
                    status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    "Sandbox output file exceeds the 50 MB limit",
                )
            content = path.read_bytes()
        finally:
            path.unlink(missing_ok=True)
            _cleanup_parent(path)

        raw_name = str(value.get("filename") or path.name).replace("\\", "/")
        filename = PurePosixPath(raw_name).name or "output.bin"
        content_type = str(value.get("content_type") or "").strip()
        if not content_type:
            content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        return GeneratedFile(filename=filename, content_type=content_type, content=content)
    if isinstance(value, dict):
        return {key: consume_sandbox_artifacts(item) for key, item in value.items()}
    if isinstance(value, list):
        return [consume_sandbox_artifacts(item) for item in value]
    return value


def sandbox_schema_value(value: Any) -> Any:
    if isinstance(value, GeneratedFile):
        return {
            "filename": value.filename,
            "content_type": value.content_type,
            "size": len(value.content),
        }
    if isinstance(value, dict):
        return {
            key: sandbox_schema_value(item)
            for key, item in value.items()
            if not str(key).startswith("__ordo_")
        }
    if isinstance(value, list):
        return [sandbox_schema_value(item) for item in value]
    return value
