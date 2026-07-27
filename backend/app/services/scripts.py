import ast
import hashlib
from typing import Any

from fastapi import HTTPException, status
from jsonschema import Draft202012Validator

BLOCKED_CALLS = {"eval", "exec", "compile", "__import__"}


def validate_script(source: str, entrypoint: str, input_schema: dict, output_schema: dict) -> str:
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, f"Python syntax error: {exc}"
        ) from exc

    functions = {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    entry_name = entrypoint.rsplit(".", 1)[-1]
    if entry_name not in functions:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, f"Entrypoint '{entry_name}' not found"
        )
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id in BLOCKED_CALLS
        ):
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY, f"Blocked call: {node.func.id}"
            )
    try:
        Draft202012Validator.check_schema(input_schema)
        if output_schema:
            Draft202012Validator.check_schema(output_schema)
    except Exception as exc:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, f"Invalid JSON Schema: {exc}"
        ) from exc
    return hashlib.sha256(source.encode()).hexdigest()


def validate_inputs(schema: dict[str, Any], inputs: dict[str, Any]) -> None:
    errors = sorted(Draft202012Validator(schema).iter_errors(inputs), key=lambda error: error.path)
    if errors:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, errors[0].message)
