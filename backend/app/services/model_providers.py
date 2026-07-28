from __future__ import annotations

import asyncio
import ipaddress
import socket
from asyncio import sleep
from copy import deepcopy
from time import perf_counter
from typing import Any
from urllib.parse import urlsplit

import httpx
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decrypt_secret
from app.models.entities import ModelProvider

SENSITIVE_HEADER_NAMES = {
    "authorization",
    "proxy-authorization",
    "x-api-key",
    "api-key",
    "cookie",
}
BLOCKED_HOSTNAMES = {
    "metadata.google.internal",
    "metadata.google.internal.",
    "instance-data",
}


def normalize_base_url(value: str) -> str:
    normalized = value.strip().rstrip("/")
    parsed = urlsplit(normalized)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("Base URL must be an http(s) URL")
    if parsed.username or parsed.password or parsed.fragment:
        raise ValueError("Base URL cannot contain credentials or a fragment")
    if len(normalized) > 500:
        raise ValueError("Base URL is too long")
    return normalized


def normalize_provider_config(value: dict[str, Any] | None) -> dict[str, Any]:
    config = deepcopy(value or {})
    api_mode = str(config.get("api_mode", "chat_completions"))
    if api_mode not in {"chat_completions", "responses"}:
        raise ValueError("API mode must be chat_completions or responses")
    timeout_seconds = int(config.get("timeout_seconds", 30))
    if not 1 <= timeout_seconds <= 300:
        raise ValueError("Timeout must be between 1 and 300 seconds")
    max_retries = int(config.get("max_retries", 1))
    if not 0 <= max_retries <= 10:
        raise ValueError("Max retries must be between 0 and 10")
    raw_headers = config.get("custom_headers", {})
    if not isinstance(raw_headers, dict):
        raise ValueError("Custom headers must be an object")
    headers: dict[str, str] = {}
    for key, item in raw_headers.items():
        name = str(key).strip()
        if not name or name.casefold() in SENSITIVE_HEADER_NAMES:
            raise ValueError(f"Sensitive custom header is not allowed: {name or '(empty)'}")
        if "\r" in name or "\n" in name or "\r" in str(item) or "\n" in str(item):
            raise ValueError("Custom headers cannot contain newlines")
        headers[name] = str(item)
    capabilities = config.get("capabilities", {})
    if not isinstance(capabilities, dict):
        raise ValueError("Capabilities must be an object")
    config.update(
        {
            "api_mode": api_mode,
            "timeout_seconds": timeout_seconds,
            "max_retries": max_retries,
            "allow_private_network": bool(config.get("allow_private_network", False)),
            "custom_headers": headers,
            "capabilities": {
                "streaming": bool(capabilities.get("streaming", True)),
                "vision": bool(capabilities.get("vision", False)),
                "tools": bool(capabilities.get("tools", False)),
                "structured_output": bool(capabilities.get("structured_output", True)),
                "embeddings": bool(capabilities.get("embeddings", False)),
            },
        }
    )
    return config


async def validate_provider_destination(base_url: str, allow_private_network: bool) -> None:
    parsed = urlsplit(base_url)
    hostname = (parsed.hostname or "").casefold()
    if hostname in BLOCKED_HOSTNAMES or hostname.endswith(".metadata.google.internal"):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Metadata endpoints are blocked")
    try:
        addresses = await asyncio.get_running_loop().getaddrinfo(
            hostname,
            parsed.port or (443 if parsed.scheme == "https" else 80),
            type=socket.SOCK_STREAM,
        )
    except socket.gaierror as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"Model host could not be resolved: {exc}") from exc
    for address in {item[4][0] for item in addresses}:
        ip = ipaddress.ip_address(address)
        if ip.is_unspecified or ip.is_multicast or ip.is_link_local or ip.is_reserved:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Model host resolves to a blocked address")
        if (ip.is_private or ip.is_loopback) and not allow_private_network:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                "Private network access must be explicitly enabled for this provider",
            )


def provider_headers(api_key: str, config: dict[str, Any]) -> dict[str, str]:
    headers = {str(key): str(value) for key, value in config.get("custom_headers", {}).items()}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


def extract_model_ids(payload: Any) -> list[str]:
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
        return []
    return [str(item["id"]) for item in payload["data"] if isinstance(item, dict) and item.get("id")]


def inference_request(api_mode: str, model: str) -> tuple[str, dict[str, Any]]:
    if api_mode == "responses":
        return "/responses", {"model": model, "input": "Reply with OK.", "max_output_tokens": 8}
    return "/chat/completions", {
        "model": model,
        "messages": [{"role": "user", "content": "Reply with OK."}],
        "max_tokens": 8,
    }


async def request_with_retries(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    *,
    max_retries: int,
    **kwargs: Any,
) -> httpx.Response:
    last_error: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            response = await client.request(method, url, **kwargs)
            response.raise_for_status()
            return response
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            last_error = exc
        except httpx.HTTPStatusError as exc:
            last_error = exc
            if exc.response.status_code < 500 and exc.response.status_code != 429:
                raise
        if attempt < max_retries:
            await sleep(min(2**attempt, 8))
    assert last_error is not None
    raise last_error


async def fetch_provider_models(
    *,
    base_url: str,
    api_key: str,
    config: dict[str, Any],
    transport: httpx.AsyncBaseTransport | None = None,
) -> dict[str, Any]:
    normalized_url = normalize_base_url(base_url)
    normalized_config = normalize_provider_config(config)
    if transport is None:
        await validate_provider_destination(
            normalized_url, bool(normalized_config.get("allow_private_network", False))
        )
    started = perf_counter()
    try:
        async with httpx.AsyncClient(
            timeout=float(normalized_config["timeout_seconds"]),
            follow_redirects=False,
            transport=transport,
        ) as client:
            response = await request_with_retries(
                client,
                "GET",
                f"{normalized_url}/models",
                max_retries=int(normalized_config["max_retries"]),
                headers=provider_headers(api_key, normalized_config),
            )
            models = extract_model_ids(response.json())[:200]
    except httpx.TimeoutException as exc:
        raise HTTPException(status.HTTP_504_GATEWAY_TIMEOUT, "Model catalog request timed out") from exc
    except httpx.HTTPStatusError as exc:
        detail = f"Model catalog request failed with HTTP {exc.response.status_code}"
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail) from exc
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"Model catalog request failed: {exc}") from exc
    return {
        "models": models,
        "latency_ms": max(0, round((perf_counter() - started) * 1000, 2)),
    }


async def test_provider_connection(
    *,
    base_url: str,
    api_key: str,
    default_model: str,
    config: dict[str, Any],
    verify_inference: bool = False,
    transport: httpx.AsyncBaseTransport | None = None,
) -> dict[str, Any]:
    normalized_url = normalize_base_url(base_url)
    normalized_config = normalize_provider_config(config)
    if transport is None:
        await validate_provider_destination(
            normalized_url, bool(normalized_config.get("allow_private_network", False))
        )
    started = perf_counter()
    models: list[str] = []
    catalog_error = ""
    inference_verified = False
    timeout = float(normalized_config["timeout_seconds"])
    headers = provider_headers(api_key, normalized_config)
    try:
        async with httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=False,
            transport=transport,
        ) as client:
            try:
                response = await request_with_retries(
                    client,
                    "GET",
                    f"{normalized_url}/models",
                    max_retries=int(normalized_config["max_retries"]),
                    headers=headers,
                )
                models = extract_model_ids(response.json())[:200]
            except (httpx.HTTPError, ValueError) as exc:
                catalog_error = str(exc)
            if verify_inference or catalog_error:
                path, body = inference_request(normalized_config["api_mode"], default_model.strip())
                response = await request_with_retries(
                    client,
                    "POST",
                    f"{normalized_url}{path}",
                    max_retries=int(normalized_config["max_retries"]),
                    headers=headers,
                    json=body,
                )
                inference_verified = True
    except httpx.TimeoutException as exc:
        raise HTTPException(status.HTTP_504_GATEWAY_TIMEOUT, "Model connection timed out") from exc
    except httpx.HTTPStatusError as exc:
        detail = f"Model connection failed with HTTP {exc.response.status_code}"
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, detail) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"Model connection failed: {exc}") from exc
    if catalog_error and not inference_verified:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"Model catalog request failed: {catalog_error}")
    default_available = default_model in models if models else None
    warning = "Model catalog is unavailable; inference succeeded" if catalog_error else ""
    if default_available is False:
        warning = "Default model was not returned by the provider catalog"
    return {
        "message": "Model provider connected",
        "status": "warning" if warning else "connected",
        "latency_ms": max(0, round((perf_counter() - started) * 1000, 2)),
        "models": models,
        "default_model_available": default_available,
        "inference_verified": inference_verified,
        "warning": warning,
        "capabilities": normalized_config["capabilities"],
    }


async def load_model_provider_runtimes(
    db: AsyncSession, workspace_id: str
) -> dict[str, dict[str, Any]]:
    providers = (
        await db.scalars(select(ModelProvider).where(ModelProvider.workspace_id == workspace_id))
    ).all()
    return {
        provider.id: {
            "id": provider.id,
            "name": provider.name,
            "base_url": provider.base_url,
            "api_key": decrypt_secret(provider.encrypted_api_key),
            "default_model": provider.default_model,
            "config": normalize_provider_config(provider.config),
        }
        for provider in providers
    }
