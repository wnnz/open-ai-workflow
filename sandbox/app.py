import json
import io
import os
import re
import secrets
import tarfile
import time

import docker
from fastapi import FastAPI, Header, HTTPException, status
from pydantic import BaseModel, Field

app = FastAPI(title="Open Workflow Sandbox", docs_url=None, redoc_url=None)
ENTRYPOINT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class ExecuteRequest(BaseModel):
    source: str = Field(max_length=1_000_000)
    entrypoint: str = "main"
    inputs: dict = {}
    timeout_seconds: int = Field(default=30, ge=1, le=300)
    memory_mb: int = Field(default=256, ge=64, le=2048)
    network_enabled: bool = False


def authorize(token: str | None) -> None:
    expected = os.getenv("SANDBOX_SHARED_SECRET")
    if not expected or not secrets.compare_digest(token or "", expected):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid sandbox token")


def build_archive(files: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w") as archive:
        for name, content in files.items():
            item = tarfile.TarInfo(name)
            item.size = len(content)
            item.mode = 0o444
            archive.addfile(item, io.BytesIO(content))
    return buffer.getvalue()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/execute")
def execute(payload: ExecuteRequest, x_sandbox_token: str | None = Header(None)) -> dict:
    authorize(x_sandbox_token)
    if not ENTRYPOINT.fullmatch(payload.entrypoint):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Invalid entrypoint")
    job_id = secrets.token_hex(12)
    runner = f'''import asyncio, contextlib, importlib.util, inspect, io, json, sys, traceback
spec = importlib.util.spec_from_file_location("user_script", "/workspace/user_script.py")
module = importlib.util.module_from_spec(spec)
logs = io.StringIO()
try:
    with contextlib.redirect_stdout(logs), contextlib.redirect_stderr(logs):
        spec.loader.exec_module(module)
        function = getattr(module, "{payload.entrypoint}")
        inputs = json.load(open("/workspace/input.json", encoding="utf-8"))
        context = {{"temp_dir": "/tmp", "network_enabled": {str(payload.network_enabled)}}}
        result = function(inputs, context)
        if inspect.isawaitable(result): result = asyncio.run(result)
    print(json.dumps({{"status":"succeeded","outputs":result,"logs":logs.getvalue().splitlines(),"error":None}}, ensure_ascii=False))
except Exception:
    print(json.dumps({{"status":"failed","outputs":{{}},"logs":logs.getvalue().splitlines(),"error":traceback.format_exc()}}, ensure_ascii=False))
'''
    archive = build_archive(
        {
            "user_script.py": payload.source.encode(),
            "input.json": json.dumps(payload.inputs).encode(),
            "runner.py": runner.encode(),
        }
    )
    started = time.monotonic()
    client = docker.from_env()
    container = None
    try:
        container = client.containers.create(
            os.getenv("SANDBOX_RUNTIME_IMAGE", "open-ai-workflow-sandbox"),
            ["python", "/workspace/runner.py"],
            network_disabled=not payload.network_enabled,
            mem_limit=f"{payload.memory_mb}m",
            nano_cpus=500_000_000,
            pids_limit=64,
            cap_drop=["ALL"],
            security_opt=["no-new-privileges"],
            tmpfs={"/tmp": "rw,noexec,nosuid,size=64m,mode=1777"},
        )
        if not container.put_archive("/workspace", archive):
            raise RuntimeError("Could not stage sandbox files")
        container.start()
        result = container.wait(timeout=payload.timeout_seconds)
        output = container.logs(stdout=True, stderr=True).decode("utf-8", errors="replace").strip().splitlines()
        if not output:
            raise RuntimeError(f"Runner exited without output: {result}")
        try:
            response = json.loads(output[-1])
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Runner exited with invalid output: {output[-10:]}") from exc
        response["elapsed_ms"] = int((time.monotonic() - started) * 1000)
        return response
    except Exception as exc:
        if container:
            try: container.kill()
            except Exception: pass
        return {"status": "failed", "outputs": {}, "logs": [], "error": str(exc), "elapsed_ms": int((time.monotonic() - started) * 1000)}
    finally:
        if container:
            try: container.remove(force=True)
            except Exception: pass
