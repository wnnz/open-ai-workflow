import io
import json
import os
import re
import secrets
import tarfile
import threading
import time
from collections.abc import Iterator
from pathlib import PurePosixPath

import docker
from fastapi import FastAPI, Header, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, model_validator

app = FastAPI(title="WeaveRun Sandbox", docs_url=None, redoc_url=None)
ENTRYPOINT = re.compile(r"^(?:[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*:)?[A-Za-z_]\w*$")
MAX_SOURCE_BYTES = 5_000_000
MAX_SOURCE_FILES = 100
MAX_INPUT_BYTES = 5_000_000
MAX_LOG_BYTES = 256_000
MAX_OUTPUT_BYTES = 2_000_000
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


def runner_source(payload: ExecuteRequest) -> str:
    return f'''import asyncio, importlib, importlib.util, inspect, io, json, sys, traceback
MAX_LOG_BYTES = {MAX_LOG_BYTES}
MAX_OUTPUT_BYTES = {MAX_OUTPUT_BYTES}
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

sys.path.insert(0, "/workspace")
sys.stdout = EventWriter("stdout")
sys.stderr = EventWriter("stderr")
try:
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
    context = {{"temp_dir": "/tmp", "network_enabled": {str(payload.network_enabled)}}}
    result = function(inputs, context)
    if inspect.isawaitable(result):
        result = asyncio.run(result)
    if not isinstance(result, dict):
        raise TypeError("Python entrypoint must return an object")
    sys.stdout.flush()
    sys.stderr.flush()
    serialized = json.dumps(result, ensure_ascii=False, default=str).encode("utf-8")
    if len(serialized) > MAX_OUTPUT_BYTES:
        raise ValueError("Script output exceeds the 2 MB limit")
    emit({{"type": "result", "status": "succeeded", "outputs": result, "error": None, "logs_truncated": logs_truncated}})
except Exception:
    sys.stdout.flush()
    sys.stderr.flush()
    emit({{"type": "result", "status": "failed", "outputs": {{}}, "error": traceback.format_exc()[-32000:], "logs_truncated": logs_truncated}})
'''


def execution_events(payload: ExecuteRequest) -> Iterator[dict]:
    job_id = payload.job_id or secrets.token_hex(12)
    files = {
        **{name: content.encode("utf-8") for name, content in normalized_files(payload.source, payload.source_files).items()},
        "input.json": json.dumps(payload.inputs, ensure_ascii=False).encode("utf-8"),
        "runner.py": runner_source(payload).encode("utf-8"),
    }
    archive = build_archive(files)
    started = time.monotonic()
    client = docker.from_env()
    container = None
    timer = None
    timed_out = threading.Event()
    saw_result = False
    try:
        container = client.containers.create(
            os.getenv("SANDBOX_RUNTIME_IMAGE", "weaverun-sandbox"),
            ["python", "/workspace/runner.py"],
            network_disabled=not payload.network_enabled,
            mem_limit=f"{payload.memory_mb}m",
            nano_cpus=500_000_000,
            pids_limit=64,
            cap_drop=["ALL"],
            security_opt=["no-new-privileges"],
            tmpfs={"/tmp": "rw,noexec,nosuid,size=64m,mode=1777"},
            labels={"weaverun.sandbox-job": job_id},
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
                    saw_result = True
                    event["elapsed_ms"] = int((time.monotonic() - started) * 1000)
                yield event
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
