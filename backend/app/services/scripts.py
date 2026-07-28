import ast
import hashlib
import json
import re
from pathlib import PurePosixPath
from typing import Any

from fastapi import HTTPException, status
from jsonschema import Draft202012Validator

MAX_SCRIPT_FILES = 100
MAX_SCRIPT_FILE_BYTES = 1_000_000
MAX_SCRIPT_BUNDLE_BYTES = 5_000_000
ENTRYPOINT = re.compile(r"^(?:[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*:)?[A-Za-z_]\w*$")


def normalize_source_files(source: str, source_files: dict[str, str] | None) -> dict[str, str]:
    files = source_files or {"main.py": source}
    if not files or len(files) > MAX_SCRIPT_FILES:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Invalid script file count")
    normalized: dict[str, str] = {}
    total_bytes = 0
    for raw_name, content in files.items():
        raw_path = str(raw_name).replace("\\", "/")
        path = PurePosixPath(raw_path)
        if (
            not raw_path
            or path.is_absolute()
            or ".." in path.parts
            or (path.parts and ":" in path.parts[0])
            or path.suffix.lower() != ".py"
            or not isinstance(content, str)
        ):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, f"Invalid script path: {raw_name}")
        name = str(path)
        size = len(content.encode("utf-8"))
        if size > MAX_SCRIPT_FILE_BYTES:
            raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, f"Script file too large: {name}")
        total_bytes += size
        if total_bytes > MAX_SCRIPT_BUNDLE_BYTES:
            raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "Script bundle too large")
        normalized[str(path)] = content
    return normalized


def entrypoint_file(entrypoint: str) -> tuple[str, str]:
    if not ENTRYPOINT.fullmatch(entrypoint):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Invalid script entrypoint")
    if ":" not in entrypoint:
        return "main.py", entrypoint
    module, function = entrypoint.split(":", 1)
    return f"{module.replace('.', '/')}.py", function


def validate_script(
    source: str,
    entrypoint: str,
    input_schema: dict,
    output_schema: dict,
    source_files: dict[str, str] | None = None,
) -> str:
    files = normalize_source_files(source, source_files)
    trees: dict[str, ast.AST] = {}
    for name, content in files.items():
        try:
            trees[name] = ast.parse(content, filename=name)
        except SyntaxError as exc:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT, f"Python syntax error in {name}: {exc}"
            ) from exc

    entry_file, entry_name = entrypoint_file(entrypoint)
    if entry_file not in trees and entry_file.endswith(".py"):
        package_entry = entry_file.removesuffix(".py") + "/__init__.py"
        entry_file = package_entry if package_entry in trees else entry_file
    if entry_file not in trees:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, f"Entrypoint module not found: {entry_file}"
        )
    functions = {
        node.name
        for node in ast.walk(trees[entry_file])
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    if entry_name not in functions:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, f"Entrypoint '{entry_name}' not found"
        )
    try:
        Draft202012Validator.check_schema(input_schema)
        if output_schema:
            Draft202012Validator.check_schema(output_schema)
    except Exception as exc:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, f"Invalid JSON Schema: {exc}"
        ) from exc
    digest_payload = {
        "files": {name: files[name] for name in sorted(files)},
        "entrypoint": entrypoint,
        "input_schema": input_schema,
        "output_schema": output_schema,
    }
    return hashlib.sha256(
        json.dumps(digest_payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def validate_inputs(schema: dict[str, Any], inputs: dict[str, Any]) -> None:
    errors = sorted(Draft202012Validator(schema).iter_errors(inputs), key=lambda error: error.path)
    if errors:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, errors[0].message)
