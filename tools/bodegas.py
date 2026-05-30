"""Contifico MCP tools: bodegas.

Split out of server.py (issue #1). Tool bodies are verbatim except that
request helpers are called through the ``server`` module (server._request
/ server._resolve_pos_token) so the test suite's monkeypatching works.
"""
import json
from typing import Any

import server
from app import mcp


# ═══════════════════════════════════════════════════════════════════════════
# BODEGAS  –  /api/v2/bodega/
# ═══════════════════════════════════════════════════════════════════════════


@mcp.tool()
async def listar_bodegas(    fecha_inicial: str | None = None,
    fecha_final: str | None = None) -> str:
    """List all warehouses in Contifico.

    OPTIONAL PARAMETERS:
      fecha_inicial (str): Modified from date, format DD/MM/YYYY.
      fecha_final (str): Modified until date, format DD/MM/YYYY.

    RETURNS:
      List of warehouse objects with: id_integracion, nombre, codigo,
      venta (bool), produccion (bool), compra (bool).
    """
    result = await server._request(
        "GET",
        "/api/v2/bodega/",
        params={"fecha_inicial": fecha_inicial, "fecha_final": fecha_final})
    return server._json(result)


@mcp.tool()
async def obtener_bodega(    id_integracion: str
) -> str:
    """Get a warehouse by its id_integracion.

    REQUIRED PARAMETERS:
      id_integracion (str): Warehouse ID (varchar 16).

    RETURNS:
      Warehouse object with: id_integracion, nombre, codigo, venta, produccion, compra.
    """
    result = await server._request("GET", f"/api/v2/bodega/{id_integracion}/")
    return server._json(result)
