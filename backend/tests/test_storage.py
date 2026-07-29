import hashlib
import io
import secrets
import shutil
from pathlib import Path
from types import SimpleNamespace

import pytest

import app.services.storage as storage


@pytest.fixture
def storage_directory(monkeypatch):
    directory = Path(".test-storage-data") / secrets.token_hex(8)
    directory.mkdir(parents=True)
    monkeypatch.setattr(
        storage,
        "get_settings",
        lambda: SimpleNamespace(storage_path=str(directory)),
    )
    yield directory
    shutil.rmtree(directory, ignore_errors=True)


def test_put_stream_writes_content_and_sanitizes_filename(storage_directory):
    content = b"local file content"

    key, digest = storage.put_stream(
        "workspace-id",
        "../unsafe\\name.txt",
        "text/plain",
        io.BytesIO(content),
        len(content),
    )

    assert key.startswith("workspaces/workspace-id/")
    assert key.endswith("/.._unsafe_name.txt")
    assert storage.object_path(key).read_bytes() == content
    assert digest == hashlib.sha256(content).hexdigest()
    assert storage.object_path(key).is_relative_to(storage_directory.resolve())


def test_put_stream_removes_partial_file_on_size_mismatch(storage_directory):
    with pytest.raises(ValueError, match="Upload size mismatch"):
        storage.put_stream(
            "workspace-id",
            "file.txt",
            "text/plain",
            io.BytesIO(b"short"),
            100,
        )

    assert list(storage_directory.rglob("*.part")) == []
    assert list(storage_directory.rglob("file.txt")) == []


@pytest.mark.parametrize("key", ["../outside", "/absolute/path", "workspaces/../outside"])
def test_object_path_rejects_unsafe_keys(storage_directory, key):
    with pytest.raises(ValueError, match="Invalid object key"):
        storage.object_path(key)


def test_remove_deletes_local_object(storage_directory):
    key, _ = storage.put("workspace-id", "file.txt", "text/plain", b"content")
    path = storage.object_path(key)

    storage.remove(key)

    assert not path.exists()
