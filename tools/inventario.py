"""Contifico MCP tools: inventario.

Split out of server.py (issue #1). Tool bodies are verbatim except that
request helpers are called through the ``server`` module (server._request
/ server._resolve_pos_token) so the test suite's monkeypatching works.
"""
import json
from typing import Any

import server
from app import mcp


# ═══════════════════════════════════════════════════════════════════════════
# MOVIMIENTOS DE INVENTARIO  –  /api/v2/movimiento-inventario/
# ═══════════════════════════════════════════════════════════════════════════


@mcp.tool()
async def listar_movimientos_inventario(    fecha_inicial: str | None = None,
    fecha_final: str | None = None,
    estado: str | None = None,
    tipo: str | None = None,
    bodega_id: str | None = None) -> str:
    """List inventory movements in Contifico.

    OPTIONAL PARAMETERS:
      fecha_inicial (str): Date range start, format DD/MM/YYYY.
      fecha_final (str): Date range end, format DD/MM/YYYY.
      estado (str): Valid values: "G"=Generated | "P"=Pending
      tipo (str): Movement type. Valid values: "ING"=Entry | "EGR"=Exit |
                  "TRA"=Transfer | "AJU"=Cost adjustment
      bodega_id (str): Filter by warehouse ID.

    RETURNS:
      List of inventory movement objects with: id_integracion, tipo, fecha,
      descripcion, bodega_id, detalles.
    """
    result = await server._request(
        "GET",
        "/api/v2/movimiento-inventario/",
        params={
            "fecha_inicial": fecha_inicial,
            "fecha_final": fecha_final,
            "estado": estado,
            "tipo": tipo,
            "bodega_id": bodega_id,
        })
    return server._json(result)


@mcp.tool()
async def obtener_movimiento_inventario(    id_integracion: str
) -> str:
    """Get an inventory movement by its id_integracion.

    REQUIRED PARAMETERS:
      id_integracion (str): Inventory movement ID (varchar 16).

    RETURNS:
      Full movement object with detalles (product_id, cantidad, precio).
    """
    result = await server._request("GET", f"/api/v2/movimiento-inventario/{id_integracion}")
    return server._json(result)


@mcp.tool()
async def crear_movimiento_inventario(    tipo: str,
    fecha: str,
    bodega_id: str,
    descripcion: str,
    detalles: list[dict[str, Any]],
    codigo: str | None = None,
    pos: str | None = None,
    bodega_destino_id: str | None = None,
    generar_asiento: bool = False) -> str:
    """⚠️ MUTATION — Create an inventory movement (entry, exit, or transfer) — POST /api/v2/movimiento-inventario/.

    REQUIRED PARAMETERS:
      tipo (str): Movement type. Valid values: "ING"=Entry | "EGR"=Exit | "TRA"=Transfer
      fecha (str): Date in DD/MM/YYYY format. Example: "30/07/2025"
      bodega_id (str): Source warehouse ID (varchar 16).
      descripcion (str): Description of the movement.
      detalles (list[dict]): List of items. Each requires:
                             {"producto_id": "...",    # varchar 16
                              "cantidad": 5.0,          # quantity
                              "precio": 10.50}          # price (REQUIRED for tipo=ING)

    CONDITIONAL PARAMETERS:
      pos (str): POS token. REQUIRED for tipo="TRA".
      bodega_destino_id (str): Destination warehouse ID. REQUIRED for tipo="TRA".

    OPTIONAL PARAMETERS:
      codigo (str): Movement reference code.
      generar_asiento (bool, default=False): If True, auto-generates accounting entry.

    RETURNS:
      Dict with created movement id_integracion and result.
    """
    body: dict[str, Any] = {
        "tipo": tipo,
        "fecha": fecha,
        "bodega_id": bodega_id,
        "descripcion": descripcion,
        "detalles": detalles,
        "generar_asiento": generar_asiento,
    }
    if codigo is not None:
        body["codigo"] = codigo
    if pos is not None:
        body["pos"] = pos
    if bodega_destino_id is not None:
        body["bodega_destino_id"] = bodega_destino_id

    result = await server._request("POST", "/api/v2/movimiento-inventario/", body=body)
    return server._json(result)
