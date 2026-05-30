"""Contifico MCP tools: contabilidad.

Split out of server.py (issue #1). Tool bodies are verbatim except that
request helpers are called through the ``server`` module (server._request
/ server._resolve_pos_token) so the test suite's monkeypatching works.
"""
import json
from typing import Any

import server
from app import mcp


# ═══════════════════════════════════════════════════════════════════════════
# ASIENTOS CONTABLES  –  /api/v2/contabilidad/asiento/
# ═══════════════════════════════════════════════════════════════════════════


@mcp.tool()
async def listar_asientos(    page: str | None = None,
    fecha_inicial: str | None = None,
    fecha_final: str | None = None,
    centro_costo: str | None = None) -> str:
    """List accounting journal entries in Contifico.

    OPTIONAL PARAMETERS:
      page (str): Page number for pagination. Example: "2"
      fecha_inicial (str): Start date, format DD/MM/YYYY.
      fecha_final (str): End date, format DD/MM/YYYY.
      centro_costo (str): Cost center id_integracion to filter by.

    RETURNS:
      Paginated list of journal entries with: id_integracion, fecha,
      glosa, and detalles.
    """
    result = await server._request(
        "GET",
        "/api/v2/contabilidad/asiento/",
        params={
            "page": page,
            "fecha_inicial": fecha_inicial,
            "fecha_final": fecha_final,
            "centro_costo": centro_costo,
        })
    return server._json(result)


@mcp.tool()
async def obtener_asiento(    id_integracion: str
) -> str:
    """Get a specific accounting journal entry by its id_integracion.

    REQUIRED PARAMETERS:
      id_integracion (str): Journal entry ID.

    RETURNS:
      Journal entry with: id, fecha (DD/MM/YYYY), glosa,
      detalles (list with: cuenta_id, centro_costo_id, tipo D/H, valor).
    """
    result = await server._request(
        "GET", f"/api/v2/contabilidad/asiento/{id_integracion}")
    return server._json(result)


# ═══════════════════════════════════════════════════════════════════════════
# CONTABILIDAD FINANCIERA (V1)  –  /api/v1/contabilidad/
# ═══════════════════════════════════════════════════════════════════════════


@mcp.tool()
async def listar_cuentas_contables(    pos_token: str | None = None
) -> str:
    """Retrieve the Chart of Accounts (Plan de Cuentas) from Contifico v1.

    OPTIONAL PARAMETERS:
      pos_token (str): POS token. Falls back to CONTIFICO_POS_TOKEN env var if omitted.

    RETURNS:
      List of accounting account objects with: id, codigo, nombre, tipo.
    """
    params = {"pos": pos_token} if pos_token else {}
    result = await server._request("GET", "/api/v1/contabilidad/cuenta-contable/", params=params)
    return server._json(result)


@mcp.tool()
async def listar_centros_costo(    pos_token: str | None = None
) -> str:
    """Retrieve cost centers from Contifico v1.

    OPTIONAL PARAMETERS:
      pos_token (str): POS token. Falls back to CONTIFICO_POS_TOKEN env var if omitted.

    RETURNS:
      List of cost center objects with: id, nombre, codigo.
    """
    params = {"pos": pos_token} if pos_token else {}
    result = await server._request("GET", "/api/v1/contabilidad/centro-costo/", params=params)
    return server._json(result)


@mcp.tool()
async def crear_asiento_contable(    fecha: str,
    glosa: str,
    detalles: list[dict],
    pos_token: str | None = None,
    extra_data: dict | None = None) -> str:
    """⚠️ MUTATION — Create a manual accounting journal entry in Contifico v1 — POST /api/v1/contabilidad/asiento/.

    REQUIRED PARAMETERS:
      fecha (str): Entry date in DD/MM/YYYY format. Example: "30/07/2025"
      glosa (str): Entry description/concept.
      detalles (list[dict]): Journal entry lines. Each line requires:
                             {"cuenta_id": "...",         # Account ID from listar_cuentas_contables
                              "centro_costo_id": "...",   # Cost center ID (optional)
                              "tipo": "D",                # "D"=Debit | "H"=Credit
                              "valor": 100.00}             # Amount

    OPTIONAL PARAMETERS:
      pos_token (str): POS token. Falls back to CONTIFICO_POS_TOKEN env var if omitted.
      extra_data (dict): Additional fields for the journal entry.

    RETURNS:
      Dict with created journal entry id_integracion.
    """
    payload = {
        "fecha": fecha,
        "glosa": glosa,
        "detalles": detalles,
    }
    if extra_data:
        payload.update(extra_data)

    params = {"pos": pos_token} if pos_token else {}
    result = await server._request("POST", "/api/v1/contabilidad/asiento/", body=payload, params=params)
    return server._json(result)
