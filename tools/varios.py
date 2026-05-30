"""Contifico MCP tools: varios.

Split out of server.py (issue #1). Tool bodies are verbatim except that
request helpers are called through the ``server`` module (server._request
/ server._resolve_pos_token) so the test suite's monkeypatching works.
"""
import json
import os
from typing import Any

import server
from app import mcp


# ═══════════════════════════════════════════════════════════════════════════
# PARÁMETROS DE EMPRESA  –  /api/v2/empresa/parametros
# ═══════════════════════════════════════════════════════════════════════════


@mcp.tool()
async def obtener_parametros_empresa() -> str:
    """Retrieve company configuration parameters from Contifico.

    Use this tool to check company settings, enabled features, and defaults
    before creating documents or persons.

    RETURNS:
      List of parameter objects with: nombre, tipo, valor.
    """
    result = await server._request("GET", "/api/v2/empresa/parametros")
    return json.dumps(result, ensure_ascii=False, default=str)


# ═══════════════════════════════════════════════════════════════════════════
# UNIDADES  –  /api/v2/unidad/
# ═══════════════════════════════════════════════════════════════════════════


@mcp.tool()
async def listar_unidades() -> str:
    """List all units of measure configured in Contifico.

    RETURNS:
      List of unit objects with: id_integracion, nombre.
    """
    result = await server._request("GET", "/api/v2/unidad/")
    return json.dumps(result, ensure_ascii=False, default=str)


@mcp.tool()
async def obtener_unidad(    id_integracion: str
) -> str:
    """Get a unit of measure by its id_integracion.

    REQUIRED PARAMETERS:
      id_integracion (str): Unit ID.

    RETURNS:
      Unit object with: id_integracion, nombre.
    """
    result = await server._request("GET", f"/api/v2/unidad/{id_integracion}")
    return json.dumps(result, ensure_ascii=False, default=str)


# ═══════════════════════════════════════════════════════════════════════════
# RECURSOS HUMANOS (V1)  –  /api/v1/rrhh/rol/
# ═══════════════════════════════════════════════════════════════════════════


@mcp.tool()
async def listar_roles_pago(    pos_token: str | None = None
) -> str:
    """Retrieve employee payroll records (roles de pago) from Contifico v1.

    OPTIONAL PARAMETERS:
      pos_token (str): POS token. Falls back to CONTIFICO_POS_TOKEN env var if omitted.

    RETURNS:
      List of payroll objects with employee, period, net pay, and deductions.
    """
    params = {"pos": pos_token} if pos_token else {}
    result = await server._request("GET", "/api/v1/rrhh/rol/", params=params)
    return json.dumps(result, ensure_ascii=False, default=str)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("MCP_PORT", 8000))
    # Default to streamable-http: it carries the caller's Authorization header
    # per tool call, which the per-request multi-tenant key model depends on.
    transport_mode = os.getenv("MCP_TRANSPORT_MODE", "http_stream").lower()
    print(f"Starting MCP Server on http://0.0.0.0:{port}/mcp ({transport_mode})")
    if transport_mode == "sse":
        app = mcp.sse_app()
    elif transport_mode == "http_stream":
        app = mcp.streamable_http_app()
    else:
        raise ValueError(f"Unknown transport mode: {transport_mode}")
    uvicorn.run(app, host="0.0.0.0", port=port)
