from __future__ import annotations

import ipaddress
import json
import socket
from typing import Any
from urllib.parse import urlsplit

import httpx
from fastapi import HTTPException, status

from app.services.model_providers import provider_headers


def ensure_safe_runtime_destination(runtime: dict[str, Any]) -> None:
    parsed = urlsplit(str(runtime.get("base_url", "")))
    hostname = (parsed.hostname or "").casefold()
    if hostname in {"metadata.google.internal", "metadata.google.internal.", "instance-data"}:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Metadata endpoints are blocked")
    try:
        addresses = socket.getaddrinfo(
            hostname,
            parsed.port or (443 if parsed.scheme == "https" else 80),
            type=socket.SOCK_STREAM,
        )
    except socket.gaierror as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"Model host could not be resolved: {exc}") from exc
    allow_private = bool(runtime.get("config", {}).get("allow_private_network", False))
    for address in {item[4][0] for item in addresses}:
        ip = ipaddress.ip_address(address)
        if ip.is_unspecified or ip.is_multicast or ip.is_link_local or ip.is_reserved:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Model host resolves to a blocked address")
        if (ip.is_private or ip.is_loopback) and not allow_private:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                "Private network access is disabled for this provider",
            )


def provider_request(
    runtime: dict[str, Any], path: str, payload: dict[str, Any]
) -> dict[str, Any]:
    provider_config = runtime.get("config", {})
    ensure_safe_runtime_destination(runtime)
    try:
        with httpx.Client(
            timeout=float(provider_config.get("timeout_seconds", 30)),
            follow_redirects=False,
        ) as client:
            response = client.post(
                f"{runtime['base_url']}{path}",
                headers=provider_headers(str(runtime.get("api_key", "")), provider_config),
                json=payload,
            )
            response.raise_for_status()
            result = response.json()
    except httpx.TimeoutException as exc:
        raise HTTPException(status.HTTP_504_GATEWAY_TIMEOUT, "Model request timed out") from exc
    except httpx.HTTPStatusError as exc:
        detail = f"Model request failed with HTTP {exc.response.status_code}"
        try:
            error = exc.response.json().get("error", {})
            message = error.get("message") if isinstance(error, dict) else None
            if message:
                detail = f"{detail}: {message}"
        except ValueError:
            pass
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail) from exc
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"Model request failed: {exc}") from exc
    if not isinstance(result, dict):
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Model response must be a JSON object")
    return result


def normalize_usage(value: Any) -> dict[str, int]:
    usage = value if isinstance(value, dict) else {}
    input_tokens = int(usage.get("input_tokens", usage.get("prompt_tokens", 0)) or 0)
    output_tokens = int(usage.get("output_tokens", usage.get("completion_tokens", 0)) or 0)
    total_tokens = int(usage.get("total_tokens", input_tokens + output_tokens) or 0)
    return {
        "input_tokens": max(0, input_tokens),
        "output_tokens": max(0, output_tokens),
        "total_tokens": max(0, total_tokens),
    }


def response_text(payload: dict[str, Any]) -> tuple[str, str, list[dict[str, Any]]]:
    if isinstance(payload.get("output_text"), str):
        return payload["output_text"], "", []
    choices = payload.get("choices")
    if isinstance(choices, list) and choices and isinstance(choices[0], dict):
        message = choices[0].get("message", {})
        if isinstance(message, dict):
            text = message.get("content", "")
            if isinstance(text, list):
                text = "".join(
                    str(item.get("text", ""))
                    for item in text
                    if isinstance(item, dict) and item.get("type") in {"text", "output_text"}
                )
            tool_calls = message.get("tool_calls", [])
            return (
                str(text or ""),
                str(message.get("reasoning_content", "") or ""),
                list(tool_calls) if isinstance(tool_calls, list) else [],
            )
    output = payload.get("output")
    if isinstance(output, list):
        text_parts: list[str] = []
        tool_calls: list[dict[str, Any]] = []
        for item in output:
            if not isinstance(item, dict):
                continue
            if item.get("type") in {"function_call", "tool_call"}:
                tool_calls.append(item)
            content = item.get("content", [])
            if isinstance(content, list):
                text_parts.extend(
                    str(part.get("text", ""))
                    for part in content
                    if isinstance(part, dict) and part.get("type") in {"output_text", "text"}
                )
        return "".join(text_parts), "", tool_calls
    return "", "", []


def image_content(value: Any, detail: str) -> list[dict[str, Any]]:
    values = value if isinstance(value, list) else [value]
    content: list[dict[str, Any]] = []
    for item in values:
        if isinstance(item, dict):
            url = item.get("url") or item.get("data_url")
        else:
            url = item
        if isinstance(url, str) and url:
            content.append({"type": "image_url", "image_url": {"url": url, "detail": detail}})
    return content


def chat_messages(config: dict[str, Any]) -> list[dict[str, Any]]:
    messages = [dict(item) for item in config.get("messages", []) if isinstance(item, dict)]
    if not messages:
        messages = [{"role": "user", "content": str(config.get("prompt", ""))}]
    context = config.get("context")
    if context:
        messages.insert(0, {"role": "system", "content": f"Context:\n{context}"})
    vision = config.get("vision", {})
    if isinstance(vision, dict) and vision.get("enabled"):
        images = image_content(vision.get("variable"), str(vision.get("detail", "high")))
        if images:
            target = next((item for item in reversed(messages) if item.get("role") == "user"), messages[-1])
            target["content"] = [
                {"type": "text", "text": str(target.get("content", ""))},
                *images,
            ]
    return messages


def response_format(config: dict[str, Any]) -> dict[str, Any] | None:
    mode = config.get("response_format", "text")
    if mode == "json_object":
        return {"type": "json_object"}
    if mode == "json_schema":
        return {
            "type": "json_schema",
            "json_schema": {
                "name": "workflow_output",
                "schema": config.get("response_schema", {}),
                "strict": True,
            },
        }
    return None


def tool_definitions(tools: Any) -> list[dict[str, Any]]:
    if not isinstance(tools, list):
        return []
    return [
        {
            "type": "function",
            "function": {
                "name": str(tool.get("name") or tool.get("id") or "tool").replace(" ", "_")[:64],
                "description": str(tool.get("description") or tool.get("name") or "Workflow tool"),
                "parameters": tool.get("parameters")
                if isinstance(tool.get("parameters"), dict)
                else {"type": "object", "properties": {}, "additionalProperties": True},
            },
        }
        for tool in tools
        if isinstance(tool, dict) and tool.get("enabled", True)
    ]


def execute_llm(runtime: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    model = str(config.get("model") or runtime.get("default_model", ""))
    provider_config = runtime.get("config", {})
    capabilities = provider_config.get("capabilities", {})
    if config.get("vision", {}).get("enabled") and not capabilities.get("vision", False):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Provider vision capability is disabled")
    if config.get("response_format") in {"json_object", "json_schema"} and not capabilities.get(
        "structured_output", True
    ):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "Provider structured output capability is disabled",
        )
    tools = tool_definitions(config.get("tools"))
    if tools and not capabilities.get("tools", False):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Provider tool capability is disabled")
    api_mode = provider_config.get("api_mode", "chat_completions")
    messages = chat_messages(config)
    if api_mode == "responses":
        payload: dict[str, Any] = {
            "model": model,
            "input": messages,
            "max_output_tokens": int(config.get("max_tokens", 1024)),
        }
        if tools:
            payload["tools"] = [{"type": "function", **item["function"]} for item in tools]
        result = provider_request(runtime, "/responses", payload)
    else:
        payload = {
            "model": model,
            "messages": messages,
            "temperature": config.get("temperature", 0.7),
            "top_p": config.get("top_p", 1),
            "max_tokens": int(config.get("max_tokens", 1024)),
        }
        output_format = response_format(config)
        if output_format:
            payload["response_format"] = output_format
        if tools:
            payload["tools"] = tools
        result = provider_request(runtime, "/chat/completions", payload)
    text, reasoning, tool_calls = response_text(result)
    output: dict[str, Any] = {
        "text": text,
        "tool_calls": tool_calls,
        "_usage": normalize_usage(result.get("usage")),
        "_model": result.get("model", model),
    }
    if config.get("reasoning", {}).get("separate"):
        output["reasoning_content"] = reasoning
    if config.get("response_format") in {"json_object", "json_schema"}:
        try:
            output["structured_output"] = json.loads(text)
        except json.JSONDecodeError as exc:
            raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Model returned invalid JSON") from exc
    return output


def execute_agent(runtime: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    llm_config = {
        "model": config.get("model") or runtime.get("default_model"),
        "messages": [
            {"role": "system", "content": str(config.get("instructions", ""))},
            {"role": "user", "content": str(config.get("query", ""))},
        ],
        "temperature": config.get("temperature", 0.3),
        "top_p": config.get("top_p", 1),
        "max_tokens": config.get("max_tokens", 2048),
        "response_format": "text",
        "tools": config.get("tools", []),
    }
    output = execute_llm(runtime, llm_config)
    output["intermediate_steps"] = []
    return output


def json_schema_for_fields(fields: list[dict[str, Any]]) -> dict[str, Any]:
    type_map = {
        "String": "string",
        "Number": "number",
        "Boolean": "boolean",
        "Object": "object",
        "Array": "array",
    }
    return {
        "type": "object",
        "properties": {
            str(field["name"]): {
                "type": type_map.get(str(field.get("type", "String")), "string"),
                "description": str(field.get("description", "")),
            }
            for field in fields
        },
        "required": [str(field["name"]) for field in fields if field.get("required")],
        "additionalProperties": False,
    }


def execute_extractor(runtime: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    fields = [item for item in config.get("fields", []) if isinstance(item, dict)]
    result = execute_llm(
        runtime,
        {
            "model": config.get("model") or runtime.get("default_model"),
            "messages": [
                {
                    "role": "system",
                    "content": "Extract the requested fields from the input. " + str(config.get("instruction", "")),
                },
                {"role": "user", "content": str(config.get("source", ""))},
            ],
            "temperature": 0,
            "top_p": 1,
            "max_tokens": config.get("max_tokens", 2048),
            "response_format": "json_schema",
            "response_schema": json_schema_for_fields(fields),
            "vision": config.get("vision", {"enabled": False}),
        },
    )
    structured = result.get("structured_output", {})
    return structured if isinstance(structured, dict) else {}
