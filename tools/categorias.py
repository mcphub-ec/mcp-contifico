"""Contifico MCP tools: categorias.

Split out of server.py (issue #1). Tool bodies are verbatim except that
request helpers are called through the ``server`` module (server._request
/ server._resolve_pos_token) so the test suite's monkeypatching works.
"""
import json
from typing import Any

import server
from app import mcp


# ═══════════════════════════════════════════════════════════════════════════
# CATEGORÍAS  –  /api/v2/categoria/
# ═══════════════════════════════════════════════════════════════════════════


@mcp.tool()
async def listar_categorias(    tipo: str | None = None,
    search_exact: str | None = None,
    modificados_desde_fecha: str | None = None) -> str:
    """List all categories in Contifico.

    OPTIONAL PARAMETERS:
      tipo (str): Category type. Valid values: "Transaccional" | "Grupo"
      search_exact (str): Filter by exact category name.
      modificados_desde_fecha (str): Modified since date, format DD/MM/YYYY.

    RETURNS:
      List of category objects with: id_integracion, nombre, tipo.
    """
    result = await server._request(
        "GET",
        "/api/v2/categoria/",
        params={
            "tipo": tipo,
            "search_exact": search_exact,
            "modificados_desde_fecha": modificados_desde_fecha,
        })
    return json.dumps(result, ensure_ascii=False, default=str)


@mcp.tool()
async def obtener_categoria(    id_integracion: str
) -> str:
    """Get a category by its id_integracion.

    REQUIRED PARAMETERS:
      id_integracion (str): Category ID (varchar 16). Example: "AB1234567890CDEF"

    RETURNS:
      Category object with: id_integracion, nombre, tipo.
    """
    result = await server._request("GET", f"/api/v2/categoria/{id_integracion}/")
    return json.dumps(result, ensure_ascii=False, default=str)


@mcp.tool()
async def crear_categoria(    nombre: str
) -> str:
    """⚠️ MUTATION — Create a new category in Contifico — POST /api/v2/categoria/.

    REQUIRED PARAMETERS:
      nombre (str): Category name (max 300 chars). Example: "Premium Customers"

    RETURNS:
      Dict with created category id_integracion and nombre.
    """
    result = await server._request("POST", "/api/v2/categoria/", body={"nombre": nombre})
    return json.dumps(result, ensure_ascii=False, default=str)


@mcp.tool()
async def actualizar_categoria(    id_integracion: str, nombre: str
) -> str:
    """⚠️ MUTATION — Update a category's name in Contifico — PUT /api/v2/categoria/{id}/.

    REQUIRED PARAMETERS:
      id_integracion (str): Category ID (varchar 16). Example: "AB1234567890CDEF"
      nombre (str): New category name (max 300 chars).

    RETURNS:
      Dict with updated category data.
    """
    result = await server._request(
        "PUT", f"/api/v2/categoria/{id_integracion}/", body={"nombre": nombre})
    return json.dumps(result, ensure_ascii=False, default=str)
