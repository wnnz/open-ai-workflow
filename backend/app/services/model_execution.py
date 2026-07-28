from __future__ import annotations

import ipaddress
import json
import socket
from collections.abc import Callable
from time import sleep
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
    max_retries = int(provider_config.get("max_retries", 1))
    response: httpx.Response | None = None
    last_error: Exception | None = None
    for attempt in range(max_retries + 1):
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
            break
        except (httpx.TimeoutException, httpx.TransportError, ValueError) as exc:
            last_error = exc
        except httpx.HTTPStatusError as exc:
            last_error = exc
            if exc.response.status_code < 500 and exc.response.status_code != 429:
                break
        if attempt < max_retries:
            sleep(min(2**attempt, 8))
    else:
        result = None
    if isinstance(last_error, httpx.TimeoutException) and (response is None or not response.is_success):
        raise HTTPException(status.HTTP_504_GATEWAY_TIMEOUT, "Model request timed out") from last_error
    if isinstance(last_error, httpx.HTTPStatusError) and (response is None or not response.is_success):
        exc = last_error
        detail = f"Model request failed with HTTP {exc.response.status_code}"
        try:
            error = exc.response.json().get("error", {})
            message = error.get("message") if isinstance(error, dict) else None
            if message:
                detail = f"{detail}: {message}"
        except ValueError:
            pass
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail) from exc
    if last_error and (response is None or not response.is_success):
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"Model request failed: {last_error}") from last_error
    if not isinstance(result, dict):
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Model response must be a JSON object")
    return result


def provider_stream_request(
    runtime: dict[str, Any],
    path: str,
    payload: dict[str, Any],
    on_token: Callable[[str], None],
) -> dict[str, Any]:
    provider_config = runtime.get("config", {})
    ensure_safe_runtime_destination(runtime)
    request_payload = {**payload, "stream": True}
    max_retries = int(provider_config.get("max_retries", 1))
    for attempt in range(max_retries + 1):
        emitted = False
        try:
            text_parts: list[str] = []
            reasoning_parts: list[str] = []
            tool_calls: dict[int, dict[str, Any]] = {}
            usage: dict[str, Any] = {}
            model = str(payload.get("model", ""))
            completed_response: dict[str, Any] | None = None
            with httpx.Client(
                timeout=float(provider_config.get("timeout_seconds", 30)),
                follow_redirects=False,
            ) as client:
                with client.stream(
                    "POST",
                    f"{runtime['base_url']}{path}",
                    headers=provider_headers(str(runtime.get("api_key", "")), provider_config),
                    json=request_payload,
                ) as response:
                    response.raise_for_status()
                    for line in response.iter_lines():
                        if not line.startswith("data:"):
                            continue
                        data = line[5:].strip()
                        if not data or data == "[DONE]":
                            continue
                        event = json.loads(data)
                        event_type = str(event.get("type", ""))
                        if event_type == "response.output_text.delta":
                            delta = str(event.get("delta", ""))
                            if delta:
                                emitted = True
                                text_parts.append(delta)
                                on_token(delta)
                        elif event_type == "response.completed" and isinstance(event.get("response"), dict):
                            completed_response = event["response"]
                        choices = event.get("choices", [])
                        if choices and isinstance(choices[0], dict):
                            delta = choices[0].get("delta", {})
                            if isinstance(delta, dict):
                                content = str(delta.get("content") or "")
                                reasoning = str(delta.get("reasoning_content") or "")
                                if content:
                                    emitted = True
                                    text_parts.append(content)
                                    on_token(content)
                                if reasoning:
                                    reasoning_parts.append(reasoning)
                                for call in delta.get("tool_calls", []) or []:
                                    index = int(call.get("index", 0))
                                    current = tool_calls.setdefault(
                                        index,
                                        {"id": call.get("id", ""), "type": "function", "function": {"name": "", "arguments": ""}},
                                    )
                                    if call.get("id"):
                                        current["id"] = call["id"]
                                    function = call.get("function", {})
                                    current["function"]["name"] += str(function.get("name") or "")
                                    current["function"]["arguments"] += str(function.get("arguments") or "")
                        if isinstance(event.get("usage"), dict):
                            usage = event["usage"]
                        if event.get("model"):
                            model = str(event["model"])
            if completed_response:
                return completed_response
            return {
                "model": model,
                "usage": usage,
                "choices": [
                    {
                        "message": {
                            "content": "".join(text_parts),
                            "reasoning_content": "".join(reasoning_parts),
                            "tool_calls": [tool_calls[index] for index in sorted(tool_calls)],
                        }
                    }
                ],
            }
        except (httpx.HTTPError, ValueError) as exc:
            if emitted or attempt >= max_retries:
                if isinstance(exc, httpx.HTTPStatusError):
                    raise HTTPException(
                        status.HTTP_502_BAD_GATEWAY,
                        f"Model stream failed with HTTP {exc.response.status_code}",
                    ) from exc
                raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"Model stream failed: {exc}") from exc
            sleep(min(2**attempt, 8))
    raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Model stream failed")


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
        if config.get("previous_response_id"):
            payload["previous_response_id"] = config["previous_response_id"]
        if tools:
            payload["tools"] = [{"type": "function", **item["function"]} for item in tools]
        callback = config.get("_stream_callback")
        result = (
            provider_stream_request(runtime, "/responses", payload, callback)
            if callable(callback) and capabilities.get("streaming", True)
            else provider_request(runtime, "/responses", payload)
        )
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
        callback = config.get("_stream_callback")
        result = (
            provider_stream_request(runtime, "/chat/completions", payload, callback)
            if callable(callback) and capabilities.get("streaming", True)
            else provider_request(runtime, "/chat/completions", payload)
        )
    text, reasoning, tool_calls = response_text(result)
    output: dict[str, Any] = {
        "text": text,
        "tool_calls": tool_calls,
        "_usage": normalize_usage(result.get("usage")),
        "_model": result.get("model", model),
        "_response_id": result.get("id"),
    }
    if config.get("reasoning", {}).get("separate"):
        output["reasoning_content"] = reasoning
    if config.get("response_format") in {"json_object", "json_schema"}:
        try:
            output["structured_output"] = json.loads(text)
        except json.JSONDecodeError as exc:
            raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Model returned invalid JSON") from exc
    return output


def execute_agent(
    runtime: dict[str, Any],
    config: dict[str, Any],
    tool_executor: Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": str(config.get("instructions", ""))},
        {"role": "user", "content": str(config.get("query", ""))},
    ]
    llm_config: dict[str, Any] = {
        "model": config.get("model") or runtime.get("default_model"),
        "messages": messages,
        "temperature": config.get("temperature", 0.3),
        "top_p": config.get("top_p", 1),
        "max_tokens": config.get("max_tokens", 2048),
        "response_format": "text",
        "tools": config.get("tools", []),
    }
    steps: list[dict[str, Any]] = []
    tools_by_name = {
        str(tool.get("name") or tool.get("id") or "tool").replace(" ", "_")[:64]: tool
        for tool in config.get("tools", [])
        if isinstance(tool, dict) and tool.get("enabled", True)
    }
    for _ in range(max(1, min(int(config.get("max_iterations", 8)), 50))):
        output = execute_llm(runtime, llm_config)
        calls = output.get("tool_calls", [])
        if not calls:
            output["intermediate_steps"] = steps if config.get("return_intermediate_steps") else []
            return output
        if not tool_executor:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Agent tools are not executable")
        assistant_calls: list[dict[str, Any]] = []
        response_tool_outputs: list[dict[str, Any]] = []
        for call in calls:
            function = call.get("function", {}) if isinstance(call, dict) else {}
            name = str(function.get("name") or call.get("name") or "")
            raw_arguments = function.get("arguments", call.get("arguments", "{}"))
            try:
                arguments = json.loads(raw_arguments) if isinstance(raw_arguments, str) else raw_arguments
            except json.JSONDecodeError as exc:
                raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Model returned invalid tool arguments") from exc
            if not isinstance(arguments, dict) or name not in tools_by_name:
                raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, f"Unknown agent tool: {name}")
            result = tool_executor(tools_by_name[name], arguments)
            call_id = str(call.get("id") or call.get("call_id") or name)
            steps.append({"tool": name, "arguments": arguments, "result": result})
            assistant_calls.append(call)
            if runtime.get("config", {}).get("api_mode") == "responses":
                response_tool_outputs.append(
                    {
                        "type": "function_call_output",
                        "call_id": call_id,
                        "output": json.dumps(result, ensure_ascii=False),
                    }
                )
            else:
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call_id,
                        "content": json.dumps(result, ensure_ascii=False),
                    }
                )
        if response_tool_outputs:
            llm_config["messages"] = response_tool_outputs
            llm_config["previous_response_id"] = output.get("_response_id")
        else:
            messages.insert(
                len(messages) - len(assistant_calls),
                {"role": "assistant", "content": output.get("text", ""), "tool_calls": assistant_calls},
            )
    raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Agent reached its iteration limit")


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
