import io
import json
import os
import re
import secrets
import tarfile
import threading
import time
from collections.abc import Iterator
from pathlib import Path, PurePosixPath

import docker
from fastapi import FastAPI, Header, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, model_validator

app = FastAPI(title="Ordo Sandbox", docs_url=None, redoc_url=None)
ENTRYPOINT = re.compile(r"^(?:[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*:)?[A-Za-z_]\w*$")
MAX_SOURCE_BYTES = 5_000_000
MAX_SOURCE_FILES = 100
MAX_INPUT_BYTES = 5_000_000
MAX_LOG_BYTES = 256_000
MAX_OUTPUT_BYTES = 2_000_000
MAX_INPUT_FILES = 100
MAX_INPUT_FILE_BYTES = 50 * 1024 * 1024
MAX_INPUT_FILE_BYTES_TOTAL = 100 * 1024 * 1024
MAX_OUTPUT_FILES = 100
MAX_OUTPUT_FILE_BYTES = 50 * 1024 * 1024
INPUT_FILE_KEY = "__ordo_object_key"
OUTPUT_FILE_KEY = "__ordo_output_file"
ARTIFACT_PATH_KEY = "__ordo_artifact_path"
active_containers: dict[str, object] = {}
active_lock = threading.Lock()


class ExecuteRequest(BaseModel):
    job_id: str | None = Field(default=None, pattern=r"^[A-Za-z0-9_-]{1,100}$")
    source: str = Field(default="", max_length=1_000_000)
    source_files: dict[str, str] = Field(default_factory=dict)
    entrypoint: str = "main"
    inputs: dict = Field(default_factory=dict)
    timeout_seconds: int = Field(default=30, ge=1, le=300)
    memory_mb: int = Field(default=256, ge=64, le=2048)
    network_enabled: bool = False

    @model_validator(mode="after")
    def validate_payload_size(self):
        files = normalized_files(self.source, self.source_files)
        if len(files) > MAX_SOURCE_FILES:
            raise ValueError("Too many script files")
        if sum(len(value.encode("utf-8")) for value in files.values()) > MAX_SOURCE_BYTES:
            raise ValueError("Script bundle too large")
        if len(json.dumps(self.inputs, ensure_ascii=False, default=str).encode("utf-8")) > MAX_INPUT_BYTES:
            raise ValueError("Script inputs too large")
        if not ENTRYPOINT.fullmatch(self.entrypoint):
            raise ValueError("Invalid entrypoint")
        return self


def authorize(token: str | None) -> None:
    expected = os.getenv("SANDBOX_SHARED_SECRET")
    if not expected or not secrets.compare_digest(token or "", expected):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid sandbox token")


def normalized_files(source: str, source_files: dict[str, str]) -> dict[str, str]:
    raw_files = source_files or {"main.py": source}
    files: dict[str, str] = {}
    for raw_name, content in raw_files.items():
        raw_path = str(raw_name).replace("\\", "/")
        path = PurePosixPath(raw_path)
        if (
            not raw_path
            or path.is_absolute()
            or ".." in path.parts
            or (path.parts and ":" in path.parts[0])
            or path.suffix.lower() != ".py"
        ):
            raise ValueError(f"Invalid script path: {raw_name}")
        files[str(path)] = content
    return files


def build_archive(files: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    directories: set[str] = set()
    for name in files:
        parent = PurePosixPath(name).parent
        while str(parent) not in {"", "."}:
            directories.add(str(parent))
            parent = parent.parent
    with tarfile.open(fileobj=buffer, mode="w") as archive:
        for directory in sorted(directories, key=lambda value: (value.count("/"), value)):
            item = tarfile.TarInfo(directory)
            item.type = tarfile.DIRTYPE
            item.mode = 0o555
            archive.addfile(item)
        for name, content in files.items():
            item = tarfile.TarInfo(name)
            item.size = len(content)
            item.mode = 0o444
            archive.addfile(item, io.BytesIO(content))
    return buffer.getvalue()


def _shared_path(root: Path, relative_path: str, message: str) -> Path:
    relative = PurePosixPath(relative_path)
    if relative.is_absolute() or not relative.parts or any(
        part in {"", ".", ".."} for part in relative.parts
    ):
        raise ValueError(message)
    path = root.joinpath(*relative.parts).resolve()
    if not path.is_relative_to(root):
        raise ValueError(message)
    return path


def stage_input_files(inputs: dict) -> tuple[dict, dict[str, bytes]]:
    storage_root = Path(os.getenv("SANDBOX_STORAGE_PATH", "/data/files")).resolve()
    staged: dict[str, bytes] = {}
    cached_paths: dict[str, str] = {}
    total_bytes = 0

    def visit(value):
        nonlocal total_bytes
        if isinstance(value, dict) and value.get(INPUT_FILE_KEY):
            object_key = str(value[INPUT_FILE_KEY])
            archive_name = cached_paths.get(object_key)
            if archive_name is None:
                if len(cached_paths) >= MAX_INPUT_FILES:
                    raise ValueError("Too many script input files")
                source = _shared_path(storage_root, object_key, "Invalid script input file")
                if not source.is_file():
                    raise ValueError("Script input file is unavailable")
                size = source.stat().st_size
                if size > MAX_INPUT_FILE_BYTES:
                    raise ValueError("Script input file exceeds the 50 MB limit")
                total_bytes += size
                if total_bytes > MAX_INPUT_FILE_BYTES_TOTAL:
                    raise ValueError("Script input files exceed the 100 MB total limit")
                raw_name = str(value.get("filename") or source.name).replace("\\", "/")
                filename = PurePosixPath(raw_name).name or "input.bin"
                archive_name = f"inputs/{len(cached_paths) + 1:04d}/{filename}"
                cached_paths[object_key] = archive_name
                staged[archive_name] = source.read_bytes()
            return {
                **{
                    key: visit(item)
                    for key, item in value.items()
                    if not str(key).startswith("__ordo_")
                },
                "path": f"/workspace/{archive_name}",
            }
        if isinstance(value, dict):
            return {
                key: visit(item)
                for key, item in value.items()
                if not str(key).startswith("__ordo_")
            }
        if isinstance(value, list):
            return [visit(item) for item in value]
        return value

    return visit(inputs), staged


def _container_file(container, path: str) -> bytes:
    reader = """import os, stat, sys
path = sys.argv[1]
limit = int(sys.argv[2])
info = os.lstat(path)
if not stat.S_ISREG(info.st_mode) or info.st_size > limit:
    raise ValueError('invalid output file')
with open(path, 'rb', buffering=0) as source:
    while chunk := source.read(1024 * 1024):
        sys.stdout.buffer.write(chunk)
"""
    result = container.exec_run(
        ["python", "-c", reader, path, str(MAX_OUTPUT_FILE_BYTES)],
        stdout=True,
        stderr=True,
        demux=True,
    )
    output = result.output
    content = (output[0] or b"") if isinstance(output, tuple) else (output or b"")
    if result.exit_code != 0:
        raise ValueError("Script output file is unavailable")
    if len(content) > MAX_OUTPUT_FILE_BYTES:
        raise ValueError("Script output file exceeds the 50 MB limit")
    return content


def collect_output_artifacts(container, outputs: dict, job_id: str) -> dict:
    artifact_root = Path(
        os.getenv("SANDBOX_ARTIFACT_PATH", "/data/sandbox-artifacts")
    ).resolve()
    job_directory = artifact_root / job_id
    created: list[Path] = []
    file_count = 0
    total_bytes = 0

    def visit(value):
        nonlocal file_count, total_bytes
        if isinstance(value, dict) and value.get(OUTPUT_FILE_KEY):
            file_count += 1
            if file_count > MAX_OUTPUT_FILES:
                raise ValueError("Too many script output files")
            relative = PurePosixPath(str(value[OUTPUT_FILE_KEY]))
            if relative.is_absolute() or not relative.parts or any(
                part in {"", ".", ".."} for part in relative.parts
            ):
                raise ValueError("Invalid script output file")
            declared_size = value.get("size")
            if (
                not isinstance(declared_size, int)
                or declared_size < 0
                or declared_size > MAX_OUTPUT_FILE_BYTES
            ):
                raise ValueError("Invalid script output file size")
            content = _container_file(
                container, f"/tmp/outputs/{relative.as_posix()}"
            )
            if len(content) != declared_size:
                raise ValueError("Script output file changed during collection")
            total_bytes += len(content)
            if total_bytes > MAX_OUTPUT_FILE_BYTES:
                raise ValueError("Script output files exceed the 50 MB total limit")
            job_directory.mkdir(parents=True, exist_ok=True)
            destination = job_directory / secrets.token_hex(16)
            destination.write_bytes(content)
            created.append(destination)
            raw_name = str(value.get("filename") or relative.name).replace("\\", "/")
            filename = PurePosixPath(raw_name).name or "output.bin"
            return {
                "filename": filename,
                "content_type": str(
                    value.get("content_type") or "application/octet-stream"
                ),
                "size": len(content),
                ARTIFACT_PATH_KEY: f"{job_id}/{destination.name}",
            }
        if isinstance(value, dict):
            return {key: visit(item) for key, item in value.items()}
        if isinstance(value, list):
            return [visit(item) for item in value]
        return value

    try:
        return visit(outputs)
    except Exception:
        for path in created:
            path.unlink(missing_ok=True)
        try:
            job_directory.rmdir()
        except OSError:
            pass
        raise


def runner_source(payload: ExecuteRequest) -> str:
    return f'''import asyncio, importlib, importlib.util, inspect, io, json, os, sys, time, traceback
from pathlib import Path, PurePosixPath
MAX_LOG_BYTES = {MAX_LOG_BYTES}
MAX_OUTPUT_BYTES = {MAX_OUTPUT_BYTES}
MAX_OUTPUT_FILES = {MAX_OUTPUT_FILES}
MAX_OUTPUT_FILE_BYTES = {MAX_OUTPUT_FILE_BYTES}
OUTPUT_FILE_KEY = {OUTPUT_FILE_KEY!r}
OUTPUT_DIR = Path("/tmp/outputs")
original_stdout = sys.stdout
log_bytes = 0
logs_truncated = False

def emit(event):
    original_stdout.write(json.dumps(event, ensure_ascii=False, default=str) + "\\n")
    original_stdout.flush()

class EventWriter(io.TextIOBase):
    def __init__(self, stream):
        self.stream = stream
        self.buffer = ""
    def write(self, value):
        global log_bytes, logs_truncated
        self.buffer += str(value)
        while "\\n" in self.buffer:
            line, self.buffer = self.buffer.split("\\n", 1)
            encoded = line.encode("utf-8", errors="replace")
            remaining = MAX_LOG_BYTES - log_bytes
            if remaining > 0:
                clipped = encoded[:remaining].decode("utf-8", errors="replace")
                emit({{"type": "log", "stream": self.stream, "message": clipped}})
                log_bytes += min(len(encoded), remaining)
            if len(encoded) > remaining:
                logs_truncated = True
        return len(value)
    def flush(self):
        if self.buffer:
            self.write("\\n")

def output_file(path, filename=None, content_type=None):
    candidate = Path(path).resolve()
    root = OUTPUT_DIR.resolve()
    try:
        relative = candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError("Output files must be created inside context['output_dir']") from exc
    return {{
        OUTPUT_FILE_KEY: relative.as_posix(),
        "filename": PurePosixPath(str(filename or relative.name).replace("\\\\", "/")).name,
        "content_type": str(content_type or "application/octet-stream"),
    }}

def normalize_output_files(value, state):
    if isinstance(value, dict) and value.get(OUTPUT_FILE_KEY):
        relative = PurePosixPath(str(value[OUTPUT_FILE_KEY]))
        if relative.is_absolute() or not relative.parts or any(part in {{"", ".", ".."}} for part in relative.parts):
            raise ValueError("Invalid script output file")
        path = (OUTPUT_DIR / Path(*relative.parts)).resolve()
        if not path.is_relative_to(OUTPUT_DIR.resolve()) or not path.is_file():
            raise ValueError("Script output file is unavailable")
        size = path.stat().st_size
        state["count"] += 1
        state["bytes"] += size
        if state["count"] > MAX_OUTPUT_FILES:
            raise ValueError("Too many script output files")
        if size > MAX_OUTPUT_FILE_BYTES or state["bytes"] > MAX_OUTPUT_FILE_BYTES:
            raise ValueError("Script output files exceed the 50 MB limit")
        return {{
            OUTPUT_FILE_KEY: relative.as_posix(),
            "filename": PurePosixPath(str(value.get("filename") or relative.name).replace("\\\\", "/")).name,
            "content_type": str(value.get("content_type") or "application/octet-stream"),
            "size": size,
        }}
    if isinstance(value, dict):
        return {{key: normalize_output_files(item, state) for key, item in value.items()}}
    if isinstance(value, list):
        return [normalize_output_files(item, state) for item in value]
    return value

sys.path.insert(0, "/workspace")
sys.stdout = EventWriter("stdout")
sys.stderr = EventWriter("stderr")
try:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    entrypoint = {payload.entrypoint!r}
    if ":" in entrypoint:
        module_name, function_name = entrypoint.split(":", 1)
        module = importlib.import_module(module_name)
    else:
        function_name = entrypoint
        spec = importlib.util.spec_from_file_location("main", "/workspace/main.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    function = getattr(module, function_name)
    inputs = json.load(open("/workspace/input.json", encoding="utf-8"))
    context = {{
        "temp_dir": "/tmp",
        "input_dir": "/workspace/inputs",
        "output_dir": str(OUTPUT_DIR),
        "output_file": output_file,
        "network_enabled": {str(payload.network_enabled)},
    }}
    result = function(inputs, context)
    if inspect.isawaitable(result):
        result = asyncio.run(result)
    if not isinstance(result, dict):
        raise TypeError("Python entrypoint must return an object")
    output_state = {{"count": 0, "bytes": 0}}
    result = normalize_output_files(result, output_state)
    sys.stdout.flush()
    sys.stderr.flush()
    serialized = json.dumps(result, ensure_ascii=False, default=str).encode("utf-8")
    if len(serialized) > MAX_OUTPUT_BYTES:
        raise ValueError("Script output exceeds the 2 MB limit")
    emit({{"type": "result", "status": "succeeded", "outputs": result, "error": None, "logs_truncated": logs_truncated}})
    if output_state["count"]:
        while True:
            time.sleep(60)
except Exception:
    sys.stdout.flush()
    sys.stderr.flush()
    emit({{"type": "result", "status": "failed", "outputs": {{}}, "error": traceback.format_exc()[-32000:], "logs_truncated": logs_truncated}})
'''


def execution_events(payload: ExecuteRequest) -> Iterator[dict]:
    job_id = payload.job_id or secrets.token_hex(12)
    started = time.monotonic()
    try:
        prepared_inputs, input_files = stage_input_files(payload.inputs)
    except Exception as exc:
        yield {
            "type": "result",
            "status": "failed",
            "outputs": {},
            "error": str(exc),
            "elapsed_ms": int((time.monotonic() - started) * 1000),
        }
        return
    files = {
        **{name: content.encode("utf-8") for name, content in normalized_files(payload.source, payload.source_files).items()},
        **input_files,
        "input.json": json.dumps(prepared_inputs, ensure_ascii=False).encode("utf-8"),
        "runner.py": runner_source(payload).encode("utf-8"),
    }
    archive = build_archive(files)
    client = docker.from_env()
    container = None
    timer = None
    timed_out = threading.Event()
    saw_result = False
    try:
        container = client.containers.create(
            os.getenv("SANDBOX_RUNTIME_IMAGE", "ordo-sandbox"),
            ["python", "/workspace/runner.py"],
            network_disabled=not payload.network_enabled,
            mem_limit=f"{payload.memory_mb}m",
            nano_cpus=500_000_000,
            pids_limit=64,
            cap_drop=["ALL"],
            security_opt=["no-new-privileges"],
            tmpfs={"/tmp": "rw,noexec,nosuid,size=64m,mode=1777"},
            labels={"ordo.sandbox-job": job_id},
        )
        with active_lock:
            active_containers[job_id] = container
        if not container.put_archive("/workspace", archive):
            raise RuntimeError("Could not stage sandbox files")
        container.start()
        def terminate_on_timeout():
            timed_out.set()
            try:
                container.kill()
            except Exception:
                pass
        timer = threading.Timer(payload.timeout_seconds, terminate_on_timeout)
        timer.daemon = True
        timer.start()
        buffer = ""
        for chunk in container.logs(stdout=True, stderr=True, stream=True, follow=True):
            buffer += chunk.decode("utf-8", errors="replace")
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                if not line.strip():
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    event = {"type": "log", "stream": "stderr", "message": line[:4000]}
                if event.get("type") == "result":
                    if event.get("status") == "succeeded" and isinstance(event.get("outputs"), dict):
                        event["outputs"] = collect_output_artifacts(
                            container, event["outputs"], job_id
                        )
                    saw_result = True
                    event["elapsed_ms"] = int((time.monotonic() - started) * 1000)
                    try:
                        container.kill()
                    except Exception:
                        pass
                yield event
                if saw_result:
                    break
            if saw_result:
                break
        if not saw_result:
            result = container.wait(timeout=payload.timeout_seconds)
            yield {
                "type": "result",
                "status": "failed",
                "outputs": {},
                "error": "Script execution timed out" if timed_out.is_set() else f"Runner exited without a result: {result}",
                "elapsed_ms": int((time.monotonic() - started) * 1000),
            }
    except Exception as exc:
        if container:
            try:
                container.kill()
            except Exception:
                pass
        yield {
            "type": "result",
            "status": "failed",
            "outputs": {},
            "error": str(exc),
            "elapsed_ms": int((time.monotonic() - started) * 1000),
        }
    finally:
        if timer:
            timer.cancel()
        with active_lock:
            active_containers.pop(job_id, None)
        if container:
            try:
                container.remove(force=True)
            except Exception:
                pass


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/execute/stream")
def execute_stream(payload: ExecuteRequest, x_sandbox_token: str | None = Header(None)):
    authorize(x_sandbox_token)

    def stream():
        for event in execution_events(payload):
            yield json.dumps(event, ensure_ascii=False, default=str) + "\n"

    return StreamingResponse(stream(), media_type="application/x-ndjson")


@app.post("/execute")
def execute(payload: ExecuteRequest, x_sandbox_token: str | None = Header(None)) -> dict:
    authorize(x_sandbox_token)
    logs: list[str] = []
    result: dict | None = None
    for event in execution_events(payload):
        if event.get("type") == "log":
            logs.append(str(event.get("message", "")))
        elif event.get("type") == "result":
            result = event
    response = result or {"status": "failed", "outputs": {}, "error": "Missing result", "elapsed_ms": 0}
    response.pop("type", None)
    response["logs"] = logs
    return response


@app.post("/executions/{job_id}/cancel")
def cancel_execution(job_id: str, x_sandbox_token: str | None = Header(None)) -> dict[str, str]:
    authorize(x_sandbox_token)
    with active_lock:
        container = active_containers.get(job_id)
    if container:
        try:
            container.kill()
        except Exception:
            pass
        return {"status": "cancelling"}
    return {"status": "not_found"}
