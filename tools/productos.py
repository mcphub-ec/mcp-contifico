"""Contifico MCP tools: productos.

Split out of server.py (issue #1). Tool bodies are verbatim except that
request helpers are called through the ``server`` module (server._request
/ server._resolve_pos_token) so the test suite's monkeypatching works.
"""
import json
from typing import Any

import server
from app import mcp


# ═══════════════════════════════════════════════════════════════════════════
# PRODUCTOS  –  /api/v2/producto/
# ═══════════════════════════════════════════════════════════════════════════


@mcp.tool()
async def listar_productos(    modificados_desde_fecha: str | None = None,
    fecha_inicial: str | None = None,
    fecha_final: str | None = None,
    filtro: str | None = None,
    page: str | None = None,
    estado: str | None = None,
    categoria_id: str | None = None) -> str:
    """List all products in Contifico (paginated at 100 per page).

    OPTIONAL PARAMETERS:
      modificados_desde_fecha (str): Filter by last change date, format DD/MM/YYYY.
      fecha_inicial (str): Last modification range start, format DD/MM/YYYY.
      fecha_final (str): Last modification range end, format DD/MM/YYYY.
      filtro (str): Search by product name or code.
      page (str): Page number for pagination (100 results/page). Example: "2"
      estado (str): Valid values: "A"=Active | "I"=Inactive
      categoria_id (str): Filter by category ID.

    RETURNS:
      Paginated list of product objects with: id_integracion, nombre, codigo,
      pvp1, pvp2, pvp3, pvp4, estado, categoria_id.
    """
    result = await server._request(
        "GET",
        "/api/v2/producto/",
        params={
            "modificados_desde_fecha": modificados_desde_fecha,
            "fecha_inicial": fecha_inicial,
            "fecha_final": fecha_final,
            "filtro": filtro,
            "page": page,
            "estado": estado,
            "categoria_id": categoria_id,
        })
    return server._json(result)


@mcp.tool()
async def obtener_producto(    id_integracion: str
) -> str:
    """Get the full details of a product by its id_integracion.

    REQUIRED PARAMETERS:
      id_integracion (str): Product ID (varchar 16).

    RETURNS:
      Full product object including: nombre, codigo, pvp1-4, stock,
      categoria_id, porcentaje_iva, unidad, etc.
    """
    result = await server._request("GET", f"/api/v2/producto/{id_integracion}")
    return server._json(result)


@mcp.tool()
async def crear_producto(    nombre: str,
    codigo: str,
    estado: str,
    pvp1: float,
    minimo: float = 0.0,
    tipo: str = "PRO",
    tipo_producto: str = "SIM",
    codigo_barra: str | None = None,
    codigo_auxiliar: str | None = None,
    categoria_id: str | None = None,
    marca_id: str | None = None,
    porcentaje_iva: int | None = None,
    pvp2: float | None = None,
    pvp3: float | None = None,
    pvp4: float | None = None,
    pvp_manual: bool | None = None,
    cuenta_venta_id: str | None = None,
    cuenta_compra_id: str | None = None,
    cuenta_costo_id: str | None = None,
    costo_maximo: float | None = None,
    para_pos: bool | None = None,
    personalizado1: str | None = None,
    personalizado2: str | None = None,
    unidad: str | None = None,
    porcentaje_ice: float | None = None,
    valor_ice: float | None = None,
    campo_catalogo: str | None = None,
    maneja_nombremanual: bool | None = None,
    porcentaje_servicio: bool | None = None) -> str:
    """⚠️ MUTATION — Create a new product in Contifico — POST /api/v2/producto/.

    REQUIRED PARAMETERS:
      nombre (str): Product name (max 300 chars). Example: "Laptop Dell"
      codigo (str): Unique product code (max 25 chars). Example: "PROD-001"
      estado (str): Valid values: "A"=Active | "I"=Inactive
      pvp1 (float): Primary sale price (e.g. retail). Example: 1200.00
      minimo (float, default=0.0): Minimum stock level.

    OPTIONAL PARAMETERS:
      tipo (str, default="PRO"): "PRO"=Product | "SER"=Service
      tipo_producto (str, default="SIM"): "SIM"=Simple (only option currently).
      codigo_barra (str): Barcode.
      codigo_auxiliar (str): Auxiliary code.
      categoria_id (str): Product category ID (from listar_categorias).
      marca_id (str): Brand ID.
      porcentaje_iva (int): VAT percentage: 0, 12, 14, 15.
      pvp2, pvp3, pvp4 (float): Alternative price levels.
      pvp_manual (bool): If True, price can be overridden at POS.
      cuenta_venta_id, cuenta_compra_id, cuenta_costo_id (str): Accounting account IDs.
      costo_maximo (float): Maximum purchase cost.
      para_pos (bool): Make available in POS.
      unidad (str): Unit of measure.
      porcentaje_ice, valor_ice (float): ICE tax fields if applicable.

    RETURNS:
      Dict with created product id_integracion and all fields.
    """
    body: dict[str, Any] = {
        "nombre": nombre,
        "codigo": codigo,
        "estado": estado,
        "pvp1": pvp1,
        "minimo": minimo,
        "tipo": tipo,
        "tipo_producto": tipo_producto,
    }
    optionals = {
        "codigo_barra": codigo_barra,
        "codigo_auxiliar": codigo_auxiliar,
        "categoria_id": categoria_id,
        "marca_id": marca_id,
        "porcentaje_iva": porcentaje_iva,
        "pvp2": pvp2,
        "pvp3": pvp3,
        "pvp4": pvp4,
        "pvp_manual": pvp_manual,
        "cuenta_venta_id": cuenta_venta_id,
        "cuenta_compra_id": cuenta_compra_id,
        "cuenta_costo_id": cuenta_costo_id,
        "costo_maximo": costo_maximo,
        "para_pos": para_pos,
        "personalizado1": personalizado1,
        "personalizado2": personalizado2,
        "unidad": unidad,
        "porcentaje_ice": porcentaje_ice,
        "valor_ice": valor_ice,
        "campo_catalogo": campo_catalogo,
        "maneja_nombremanual": maneja_nombremanual,
        "porcentaje_servicio": porcentaje_servicio,
    }
    body.update(server._drop_none(optionals))

    result = await server._request("POST", "/api/v2/producto/", body=body)
    return server._json(result)


@mcp.tool()
async def actualizar_producto(    id_integracion: str,
    nombre: str,
    codigo: str,
    estado: str,
    pvp1: float,
    minimo: float = 0.0,
    tipo: str = "PRO",
    tipo_producto: str = "SIM",
    codigo_barra: str | None = None,
    codigo_auxiliar: str | None = None,
    categoria_id: str | None = None,
    marca_id: str | None = None,
    porcentaje_iva: int | None = None,
    pvp2: float | None = None,
    pvp3: float | None = None,
    pvp4: float | None = None,
    pvp_manual: bool | None = None,
    cuenta_venta_id: str | None = None,
    cuenta_compra_id: str | None = None,
    cuenta_costo_id: str | None = None,
    costo_maximo: float | None = None,
    para_pos: bool | None = None,
    personalizado1: str | None = None,
    personalizado2: str | None = None,
    unidad: str | None = None,
    porcentaje_ice: float | None = None,
    valor_ice: float | None = None,
    campo_catalogo: str | None = None,
    maneja_nombremanual: bool | None = None,
    porcentaje_servicio: bool | None = None) -> str:
    """⚠️ MUTATION — Update an existing product in Contifico — PUT /api/v2/producto/{id}.

    REQUIRED PARAMETERS:
      id_integracion (str): Product ID to update.
      nombre, codigo, estado, pvp1 (float), minimo (float): Same as crear_producto.

    OPTIONAL PARAMETERS:
      Same optional fields as crear_producto.

    RETURNS:
      Dict with updated product data.
    """
    body: dict[str, Any] = {
        "nombre": nombre,
        "codigo": codigo,
        "estado": estado,
        "pvp1": pvp1,
        "minimo": minimo,
        "tipo": tipo,
        "tipo_producto": tipo_producto,
    }
    optionals = {
        "codigo_barra": codigo_barra,
        "codigo_auxiliar": codigo_auxiliar,
        "categoria_id": categoria_id,
        "marca_id": marca_id,
        "porcentaje_iva": porcentaje_iva,
        "pvp2": pvp2,
        "pvp3": pvp3,
        "pvp4": pvp4,
        "pvp_manual": pvp_manual,
        "cuenta_venta_id": cuenta_venta_id,
        "cuenta_compra_id": cuenta_compra_id,
        "cuenta_costo_id": cuenta_costo_id,
        "costo_maximo": costo_maximo,
        "para_pos": para_pos,
        "personalizado1": personalizado1,
        "personalizado2": personalizado2,
        "unidad": unidad,
        "porcentaje_ice": porcentaje_ice,
        "valor_ice": valor_ice,
        "campo_catalogo": campo_catalogo,
        "maneja_nombremanual": maneja_nombremanual,
        "porcentaje_servicio": porcentaje_servicio,
    }
    body.update(server._drop_none(optionals))

    result = await server._request("PUT", f"/api/v2/producto/{id_integracion}", body=body)
    return server._json(result)


@mcp.tool()
async def obtener_stock_producto(    id_integracion: str
) -> str:
    """Get the stock breakdown by warehouse for a specific product.

    REQUIRED PARAMETERS:
      id_integracion (str): Product ID (varchar 16).

    RETURNS:
      List of stock entries per warehouse: bodega_nombre, bodega_id, cantidad.
    """
    result = await server._request("GET", f"/api/v2/producto/{id_integracion}/stock/")
    return server._json(result)
