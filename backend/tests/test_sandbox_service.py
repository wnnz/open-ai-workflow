import importlib.util
import shutil
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


@pytest.fixture(scope="module")
def sandbox_service():
    source = Path(__file__).parents[2] / "sandbox" / "app.py"
    spec = importlib.util.spec_from_file_location("ordo_sandbox_service", source)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    existing_docker_module = sys.modules.get("docker")
    sys.modules["docker"] = SimpleNamespace()
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
        yield module
    finally:
        sys.modules.pop(spec.name, None)
        if existing_docker_module is None:
            sys.modules.pop("docker", None)
        else:
            sys.modules["docker"] = existing_docker_module


class FakeContainer:
    def __init__(self, content: bytes, exit_code: int = 0):
        self.content = content
        self.exit_code = exit_code
        self.command = None

    def exec_run(self, command, **kwargs):
        self.command = command
        assert kwargs == {"stdout": True, "stderr": True, "demux": True}
        return SimpleNamespace(
            exit_code=self.exit_code,
            output=(self.content, b""),
        )


def test_collect_output_artifacts_reads_tmpfs_file_through_exec(
    sandbox_service, monkeypatch
):
    artifact_root = Path("test-sandbox-service-artifacts").resolve()
    shutil.rmtree(artifact_root, ignore_errors=True)
    monkeypatch.setenv("SANDBOX_ARTIFACT_PATH", str(artifact_root))
    container = FakeContainer(b"docx-content")
    try:
        result = sandbox_service.collect_output_artifacts(
            container,
            {
                "file": {
                    sandbox_service.OUTPUT_FILE_KEY: "answered.docx",
                    "filename": "answered.docx",
                    "content_type": "application/test",
                    "size": 12,
                }
            },
            "test-job",
        )

        descriptor = result["file"]
        artifact = artifact_root / descriptor[sandbox_service.ARTIFACT_PATH_KEY]
        assert artifact.read_bytes() == b"docx-content"
        assert container.command[0:2] == ["python", "-c"]
        assert container.command[3] == "/tmp/outputs/answered.docx"
    finally:
        shutil.rmtree(artifact_root, ignore_errors=True)


def test_collect_output_artifacts_rejects_changed_file_size(
    sandbox_service, monkeypatch
):
    artifact_root = Path("test-sandbox-service-artifacts").resolve()
    shutil.rmtree(artifact_root, ignore_errors=True)
    monkeypatch.setenv("SANDBOX_ARTIFACT_PATH", str(artifact_root))
    try:
        with pytest.raises(ValueError, match="changed during collection"):
            sandbox_service.collect_output_artifacts(
                FakeContainer(b"changed"),
                {
                    "file": {
                        sandbox_service.OUTPUT_FILE_KEY: "answered.docx",
                        "filename": "answered.docx",
                        "content_type": "application/test",
                        "size": 12,
                    }
                },
                "test-job",
            )
    finally:
        shutil.rmtree(artifact_root, ignore_errors=True)
