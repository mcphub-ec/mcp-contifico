"""HTTP layer for the Contifico MCP server.

Split out of server.py (issue #1). Named _http.py (leading underscore) on
purpose so it never shadows the stdlib http package.

The two mutable security flags are read through the ``server`` module at call
time (``server.ALLOW_ENV_KEY_FALLBACK`` / ``server.CONTIFICO_READONLY``) so
that runtime monkeypatching on ``server`` — as the test suite does — takes
effect. ``server`` re-exports these helpers and flags.
"""
import os
import json
from typing import Any

import httpx

import server
from app import mcp
from config import (
    CONTIFICO_BASE_URL,
    HTTP_TIMEOUT,
    _SAFE_PATH,
    logger,
)


def _request_http_headers() -> Any:
    """Return the incoming MCP request's HTTP headers, or None outside an HTTP request.

    Works for the SSE and streamable-http transports, where FastMCP exposes the
    underlying Starlette ``Request`` via the per-call request context.
    """
    try:
        request = mcp.get_context().request_context.request
    except (LookupError, ValueError, AttributeError):
        return None
    return getattr(request, "headers", None)


def _resolve_api_key() -> str:
    """Resolve the caller's Contifico API key for the current request.

    Priority:
      1. ``Authorization: Bearer <key>`` header on the incoming MCP request
         (multi-tenant: each caller passes their own key).
      2. ``CONTIFICO_API_KEY`` env var — LOCAL DEV ONLY fallback.

    The resolved key is used only for this request and is never stored or logged.
    """
    headers = _request_http_headers()
    if headers:
        auth = headers.get("authorization")
        if auth:
            if auth[:7].lower() == "bearer ":
                auth = auth[7:]
            return auth.strip()
    # Fail closed: only fall back to the server env key when explicitly allowed
    # (local single-tenant dev). In multi-tenant prod a missing header must NOT
    # silently reuse another tenant's key.
    if server.ALLOW_ENV_KEY_FALLBACK:
        return os.environ.get("CONTIFICO_API_KEY", "")
    return ""


def _build_headers() -> dict[str, str]:
    """Build Contifico auth headers from the per-request API key."""
    resolved = _resolve_api_key()
    if not resolved:
        raise ValueError(
            "No Contifico API key resolved. Send it as 'Authorization: Bearer <key>' "
            "on the MCP request (multi-tenant), or set CONTIFICO_API_KEY (local dev only)."
        )
    return {
        "Authorization": resolved,
        "Content-Type": "application/json",
    }


_SENSITIVE_KEYS = {
    "pos", "authorization", "api_key", "apikey", "token", "key", "secret",
    "password", "pos_token",
}


def _safe_params(params: dict[str, Any] | None) -> dict[str, Any] | None:
    """Copy of params with sensitive values redacted before logging."""
    if not params:
        return params
    return {
        k: ("***" if k.lower() in _SENSITIVE_KEYS else v)
        for k, v in params.items()
    }



async def _request(
    method: str,
    path: str,
    *,
    headers: dict[str, str] | None = None,
    params: dict[str, Any] | None = None,
    body: dict[str, Any] | None = None) -> dict | list | str:
    """Ejecuta una petición HTTP contra la API de Contifico y devuelve la respuesta."""
    # Read-only guard (server-side defense-in-depth; Socio also filters write
    # tools client-side). Blocks mutating methods unless writes are enabled.
    if server.CONTIFICO_READONLY and method.upper() not in ("GET", "HEAD"):
        return {
            "error": True,
            "status_code": 403,
            "detail": "Server is in read-only mode; write operations are disabled.",
        }
    # Reject any path that isn't slash-delimited alphanumeric segments — blocks
    # traversal / query-fragment injection via interpolated id values.
    if not _SAFE_PATH.match(path):
        raise ValueError(f"Unsafe request path rejected: {path!r}")

    url = f"{CONTIFICO_BASE_URL}{path}"
    # Limpiar parámetros vacíos / None
    if params:
        params = {k: v for k, v in params.items() if v is not None and v != ""}

    logger.info("%s %s params=%s", method.upper(), url, _safe_params(params))

    req_headers = _build_headers()
    if headers:
        req_headers.update(headers)

    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        resp = await client.request(
            method,
            url,
            headers=req_headers,
            params=params,
            json=body)
        logger.info("Respuesta HTTP %s", resp.status_code)

        if resp.status_code >= 400:
            # Log the upstream body server-side (truncated) but return a generic
            # message — never echo Contifico's raw error body to the caller
            # (it can leak another tenant's data/identifiers).
            logger.warning(
                "Contifico error %s on %s: %s",
                resp.status_code, path, resp.text[:500],
            )
            return {
                "error": True,
                "status_code": resp.status_code,
                "detail": f"Contifico returned HTTP {resp.status_code}.",
            }

        # Contifico puede devolver un cuerpo vacío en 204/201
        if not resp.text.strip():
            return {"ok": True, "status_code": resp.status_code}

        try:
            return resp.json()
        except Exception:
            return resp.text


def _resolve_pos_token(pos_token: str) -> str:
    """Validate and return the Contifico POS token."""
    resolved = pos_token or os.environ.get("CONTIFICO_POS_TOKEN", "")
    if not resolved:
        raise ValueError(
            "Contifico pos_token is required for write operations. "
            "CONTIFICO_POS_TOKEN env var is required for POS operations."
        )
    return resolved
