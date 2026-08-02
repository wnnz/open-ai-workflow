from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

import app.services.sandbox_artifacts as sandbox_artifacts
from app.services.document_processing import GeneratedFile


def test_consume_sandbox_artifacts_returns_generated_file_and_cleans_up(
    monkeypatch,
):
    artifact = Path("test-sandbox-artifact.bin")
    try:
        monkeypatch.setattr(
            sandbox_artifacts,
            "get_settings",
            lambda: SimpleNamespace(sandbox_artifact_path="."),
        )
        artifact.write_bytes(b"docx-content")

        result = sandbox_artifacts.consume_sandbox_artifacts(
            {
                "file": {
                    "filename": "answered.docx",
                    "content_type": "application/test",
                    "size": 12,
                    "__ordo_artifact_path": artifact.name,
                }
            }
        )

        assert result == {
            "file": GeneratedFile("answered.docx", "application/test", b"docx-content")
        }
        assert not artifact.exists()
    finally:
        artifact.unlink(missing_ok=True)


def test_consume_sandbox_artifacts_rejects_path_traversal(monkeypatch):
    monkeypatch.setattr(
        sandbox_artifacts,
        "get_settings",
        lambda: SimpleNamespace(sandbox_artifact_path="."),
    )

    with pytest.raises(HTTPException) as error:
        sandbox_artifacts.consume_sandbox_artifacts(
            {
                "filename": "secret.txt",
                "content_type": "text/plain",
                "__ordo_artifact_path": "../secret.txt",
            }
        )

    assert error.value.status_code == 422


def test_sandbox_schema_value_exposes_generated_file_metadata():
    assert sandbox_artifacts.sandbox_schema_value(
        {"file": GeneratedFile("answer.docx", "application/test", b"123")}
    ) == {
        "file": {
            "filename": "answer.docx",
            "content_type": "application/test",
            "size": 3,
        }
    }
