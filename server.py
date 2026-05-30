"""Contifico MCP server.

Exposes Contifico API endpoints as MCP tools using the Model Context Protocol.

Wires together the split modules (issue #1). This module is the canonical
runtime namespace: it re-exports the config flags, the HTTP helpers, and the
FastMCP instance, then imports every tools.* module so their @mcp.tool()
decorators register on the shared `mcp`. _http.py and the tools resolve the
mutable flags / request helpers through THIS module at call time, so runtime
monkeypatching (as the test suite does) takes effect.
"""
# Config flags first — _http.py reads server.ALLOW_ENV_KEY_FALLBACK /
# server.CONTIFICO_READONLY at call time, so they must exist on this module
# before any tool is invoked.
from config import (  # noqa: F401
    CONTIFICO_BASE_URL,
    HTTP_TIMEOUT,
    ALLOW_ENV_KEY_FALLBACK,
    CONTIFICO_READONLY,
    _SAFE_PATH,
    logger,
    _env_flag,
    _JsonLogFormatter,
)
from app import mcp  # noqa: F401
from _http import (  # noqa: F401
    _request_http_headers,
    _resolve_api_key,
    _build_headers,
    _SENSITIVE_KEYS,
    _safe_params,
    _request,
    _resolve_pos_token,
    _json,
    _drop_none,
)

# Importing each tools module registers its @mcp.tool() functions on `mcp`.
import tools.personas  # noqa: F401,E402
import tools.categorias  # noqa: F401,E402
import tools.bodegas  # noqa: F401,E402
import tools.productos  # noqa: F401,E402
import tools.inventario  # noqa: F401,E402
import tools.documentos  # noqa: F401,E402
import tools.bancos  # noqa: F401,E402
import tools.varios  # noqa: F401,E402
import tools.contabilidad  # noqa: F401,E402

__all__ = ["mcp", "_json", "_drop_none"]
