"""Contifico MCP tools: bancos.

Split out of server.py (issue #1). Tool bodies are verbatim except that
request helpers are called through the ``server`` module (server._request
/ server._resolve_pos_token) so the test suite's monkeypatching works.
"""
import json
from typing import Any

import server
from app import mcp


# ═══════════════════════════════════════════════════════════════════════════
# CUENTAS BANCARIAS  –  /api/v2/banco/cuenta/
# ═══════════════════════════════════════════════════════════════════════════


@mcp.tool()
async def listar_cuentas_bancarias() -> str:
    """List all bank accounts configured in Contifico.

    RETURNS:
      List of bank account objects with: id_integracion, nombre, numero,
      tipo_cuenta (CC=Checking/CA=Savings), estado (A/I), saldo_inicial,
      fecha_corte, cuenta_contable, nombre_banco.
    """
    result = await server._request("GET", "/api/v2/banco/cuenta/")
    return server._json(result)


@mcp.tool()
async def obtener_cuenta_bancaria(    id_integracion: str
) -> str:
    """Get a bank account by its id_integracion.

    REQUIRED PARAMETERS:
      id_integracion (str): Bank account ID (varchar 16).

    RETURNS:
      Bank account object with all fields.
    """
    result = await server._request("GET", f"/api/v2/banco/cuenta/{id_integracion}/")
    return server._json(result)


# ═══════════════════════════════════════════════════════════════════════════
# MOVIMIENTOS BANCARIOS (V1)  –  /api/v1/banco/movimiento/
# ═══════════════════════════════════════════════════════════════════════════


@mcp.tool()
async def listar_movimientos_bancarios(    fecha_inicial: str | None = None,
    fecha_final: str | None = None,
    pos_token: str | None = None) -> str:
    """Retrieve bank movements (bank statements/cartolas) from Contifico v1.

    OPTIONAL PARAMETERS:
      fecha_inicial (str): Start date, format DD/MM/YYYY.
      fecha_final (str): End date, format DD/MM/YYYY.
      pos_token (str): POS token. Falls back to CONTIFICO_POS_TOKEN env var if omitted.

    RETURNS:
      List of bank movement objects with: fecha, descripcion, monto, tipo (D/C).
    """
    params = {}
    if fecha_inicial:
        params["fecha_inicial"] = fecha_inicial
    if fecha_final:
        params["fecha_final"] = fecha_final
    if pos_token:
        params["pos"] = pos_token

    result = await server._request("GET", "/api/v1/banco/movimiento/", params=params if params else None)
    return server._json(result)
