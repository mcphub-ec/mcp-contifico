"""
Contifico MCP Server v2
=======================
MCP server for Contifico REST API v2 — cloud accounting platform for Ecuador.
Manages customers, suppliers, products, invoices, credit notes, inventory,
accounting entries, and payroll.

Technical reference: docs/openapiv2.yaml
"""

import os
import json
import logging
from typing import Any
from dotenv import load_dotenv

import httpx
from mcp.server.fastmcp import FastMCP

# Cargar variables desde el archivo .env
load_dotenv()


# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format='{"time":"%(asctime)s", "level":"%(levelname)s", "name":"%(name)s", "message":"%(message)s"}',
)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("contifico-mcp")

CONTIFICO_BASE_URL = os.environ.get(
    "CONTIFICO_BASE_URL", "https://api.contifico.com/sistema"
)

HTTP_TIMEOUT = float(os.environ.get("CONTIFICO_HTTP_TIMEOUT", "30"))

mcp = FastMCP(
    "contifico",
    host="0.0.0.0",
    instructions=(
        "MCP server for Contifico REST API v2 — cloud accounting system for Ecuador. "
        "Manages: people (customers/suppliers/employees), products, documents (invoices, "
        "credit notes, quotations), categories, warehouses, inventory movements, "
        "collections, bank accounts, payment methods, accounting entries, and payroll. "
        "Credentials are loaded from CONTIFICO_API_KEY env var. "
        "WRITE OPERATIONS: crear_persona and actualizar_persona also require `pos_token`. "
        "PAGINATION: listar_* tools return 100 results per page. Use 'page' parameter to paginate. "
        "DATE FORMAT: All date fields use DD/MM/YYYY format. Example: '30/07/2025'. To filter documents by issue date, use 'fecha_inicial' and 'fecha_final' instead of generic date fields. "
        "DOCUMENT TYPES: FAC=Invoice, LQC=Purchase settlement, PRE=Pre-invoice, "
        "NCT=Credit note, COT=Quotation, OCV=Purchase/Sale order, NVE=Sales note. "
        "PERSON TYPES: N=Natural, J=Legal entity, I=No ID (needs personaasociada_id), P=Plate. "
        "INVENTORY TYPES: ING=Entry, EGR=Exit, TRA=Transfer (requires bodega_destino_id)."
    ))

# ---------------------------------------------------------------------------
# Cliente HTTP reutilizable
# ---------------------------------------------------------------------------


def _build_headers() -> dict[str, str]:
    """Build auth headers for a specific account."""
    resolved = os.environ.get("CONTIFICO_API_KEY", "")
    if not resolved:
        raise ValueError(
            "api_key is required for this MCP. Pass it as a tool parameter."
        )
    return {
        "Authorization": resolved,
        "Content-Type": "application/json",
    }



async def _request(
    method: str,
    path: str,
    *,    params: dict[str, Any] | None = None,
    body: dict[str, Any] | None = None) -> dict | list | str:
    """Ejecuta una petición HTTP contra la API de Contifico y devuelve la respuesta."""
    url = f"{CONTIFICO_BASE_URL}{path}"
    # Limpiar parámetros vacíos / None
    if params:
        params = {k: v for k, v in params.items() if v is not None and v != ""}

    logger.info("%s %s params=%s", method.upper(), url, params)

    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        resp = await client.request(
            method,
            url,
            headers=_build_headers(),
            params=params,
            json=body)
        logger.info("Respuesta HTTP %s", resp.status_code)

        if resp.status_code >= 400:
            error_body = resp.text
            return {
                "error": True,
                "status_code": resp.status_code,
                "detail": error_body,
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


# ═══════════════════════════════════════════════════════════════════════════
# PERSONAS  –  /api/v2/persona/
# ═══════════════════════════════════════════════════════════════════════════


@mcp.tool()
async def listar_personas(    search: str | None = None,
    modificados_desde_fecha: str | None = None,
    estado: str | None = None,
    fecha_inicial: str | None = None,
    fecha_final: str | None = None,
    es_proveedor: str | None = None,
    es_cliente: str | None = None,
    tipo: str | None = None,
    page: str | None = None,
    categoria_id: str | None = None) -> str:
    """Search and list people (customers, suppliers, employees) in Contifico.

    Use this tool to find existing customers before creating a document, or to
    get id_integracion values for other operations.

    OPTIONAL PARAMETERS:
      search (str): Search in razon_social, nombre_comercial, cedula, ruc.
                    Example: "Juan Perez"
      modificados_desde_fecha (str): Filter by last modification date. Format DD/MM/YYYY.
      estado (str): Valid values: "A"=Active | "I"=Inactive
      fecha_inicial (str): Date range start, format DD/MM/YYYY.
      fecha_final (str): Date range end, format DD/MM/YYYY.
      es_proveedor (str): Filter suppliers. Valid values: "1"=True | "0"=False
      es_cliente (str): Filter customers. Valid values: "1"=True | "0"=False
      tipo (str): Person type. Valid values: "N"=Natural | "J"=Legal entity |
                  "I"=No ID | "P"=Plate
      page (str): Page number for pagination. Results: 100 per page. Example: "2"
      categoria_id (str): Filter by person category ID.

    RETURNS:
      Paginated list of person objects with: id_integracion, cedula, ruc,
      razon_social, tipo, es_cliente, es_proveedor, email, telefonos, direccion.
    """
    result = await _request(
        "GET",
        "/api/v2/persona/",
        params={
            "search": search,
            "modificados_desde_fecha": modificados_desde_fecha,
            "estado": estado,
            "fecha_inicial": fecha_inicial,
            "fecha_final": fecha_final,
            "es_proveedor": es_proveedor,
            "es_cliente": es_cliente,
            "tipo": tipo,
            "page": page,
            "categoria_id": categoria_id,
        })
    return json.dumps(result, ensure_ascii=False, default=str)


@mcp.tool()
async def obtener_persona(    id_integracion: str
) -> str:
    """Obtiene una persona por su id_integracion (varchar 16).

    Devuelve todos los campos: id, ruc, cedula, razon_social, tipo,
    es_cliente, es_proveedor, email, telefonos, direccion, etc.
    """
    result = await _request("GET", f"/api/v2/persona/{id_integracion}/")
    return json.dumps(result, ensure_ascii=False, default=str)


@mcp.tool()
async def crear_persona(    pos_token: str,
    tipo: str,
    razon_social: str,
    es_cliente: bool,
    es_proveedor: bool,
    cedula: str = "",
    ruc: str | None = None,
    nombre_comercial: str | None = None,
    email: str | None = None,
    telefonos: str | None = None,
    direccion: str | None = None,
    placa: str | None = None,
    es_vendedor: bool = False,
    es_empleado: bool = False,
    es_corporativo: bool = False,
    es_extranjero: bool = False,
    aplicar_cupo: bool = False,
    porcentaje_descuento: float | None = None,
    adicionales_cliente: str | None = None,
    adicionales_proveedor: str | None = None,
    personaasociada_id: str | None = None,
    banco_codigo_id: str | None = None,
    numero_tarjeta: str | None = None,
    tipo_cuenta: str | None = None,
    origen: str | None = None) -> str:
    """⚠️ MUTATION — Create a person (customer, supplier, or employee) in Contifico — POST /api/v2/persona/.

    REQUIRED PARAMETERS:
      api_key (str): Contifico API key for the account.
      pos_token (str): Contifico POS token required for write operations.
                  "I"=No ID (requires personaasociada_id), "P"=Plate (requires placa).
      razon_social (str): Full name or company name (max 300 chars).
      es_cliente (bool): True if this person is a customer.
      es_proveedor (bool): True if this person is a supplier.
                           At least one of es_cliente/es_proveedor MUST be True.
      cedula (str): Cedula number (10 digits). Required for all types except "I".
                    Example: "0912345678". Use empty string "" if not applicable.

    CONDITIONAL PARAMETERS:
      ruc (str): RUC (13 digits). REQUIRED for tipo="J". Example: "0912345678001"
      placa (str): Vehicle plate. REQUIRED for tipo="P". Example: "PBC-454"
      personaasociada_id (str): Associated person ID. REQUIRED for tipo="I".

    OPTIONAL PARAMETERS:
      nombre_comercial (str): Trade name.
      email (str): Email address.
      telefonos (str): Phone numbers.
      direccion (str): Address.
      es_vendedor (bool, default=False): Is a salesperson.
      es_empleado (bool, default=False): Is an employee.
      es_corporativo (bool, default=False): Is a corporate account.
      es_extranjero (bool, default=False): Is a foreign entity.
      aplicar_cupo (bool, default=False): Apply credit limit.
      porcentaje_descuento (float): Default discount percentage.
      adicionales_cliente (str): Customer additional data (JSON string).
      adicionales_proveedor (str): Supplier additional data (JSON string).
      banco_codigo_id (str): Bank ID for direct debit.
      numero_tarjeta (str): Card number for direct debit.
      tipo_cuenta (str): Account type ("CC"=Checking, "CA"=Savings).
      origen (str): Customer origin (for CRM segmentation).

    RETURNS:
      Dict with created person id_integracion and all fields.
    """
    pos = _resolve_pos_token(pos_token)
    body: dict[str, Any] = {
        "tipo": tipo,
        "razon_social": razon_social,
        "es_cliente": es_cliente,
        "es_proveedor": es_proveedor,
        "cedula": cedula,
        "es_vendedor": es_vendedor,
        "es_empleado": es_empleado,
        "es_corporativo": es_corporativo,
        "es_extranjero": es_extranjero,
        "aplicar_cupo": aplicar_cupo,
    }
    # Opcionales – sólo incluir si se proporcionan
    optionals = {
        "ruc": ruc,
        "nombre_comercial": nombre_comercial,
        "email": email,
        "telefonos": telefonos,
        "direccion": direccion,
        "placa": placa,
        "porcentaje_descuento": porcentaje_descuento,
        "adicionales_cliente": adicionales_cliente,
        "adicionales_proveedor": adicionales_proveedor,
        "personaasociada_id": personaasociada_id,
        "banco_codigo_id": banco_codigo_id,
        "numero_tarjeta": numero_tarjeta,
        "tipo_cuenta": tipo_cuenta,
        "origen": origen,
    }
    for k, v in optionals.items():
        if v is not None:
            body[k] = v

    result = await _request(
        "POST", "/api/v2/persona/", params={"pos": pos}, body=body)
    return json.dumps(result, ensure_ascii=False, default=str)


@mcp.tool()
async def actualizar_persona(    pos_token: str,
    id_integracion: str,
    tipo: str,
    razon_social: str,
    es_cliente: bool,
    es_proveedor: bool,
    cedula: str = "",
    ruc: str | None = None,
    nombre_comercial: str | None = None,
    email: str | None = None,
    telefonos: str | None = None,
    direccion: str | None = None,
    placa: str | None = None,
    es_vendedor: bool = False,
    es_empleado: bool = False,
    es_corporativo: bool = False,
    es_extranjero: bool = False,
    aplicar_cupo: bool = False,
    porcentaje_descuento: float | None = None,
    adicionales_cliente: str | None = None,
    adicionales_proveedor: str | None = None,
    personaasociada_id: str | None = None,
    banco_codigo_id: str | None = None,
    numero_tarjeta: str | None = None,
    tipo_cuenta: str | None = None) -> str:
    """⚠️ MUTATION — Update an existing person by id_integracion in Contifico — PUT /api/v2/persona/{id}/.

    REQUIRED PARAMETERS:
      api_key (str): Contifico API key for the account.
      pos_token (str): Contifico POS token required for write operations.
      id_integracion (str): Person ID to update. Example: "AB1234567890CDEF"
      tipo, razon_social, es_cliente, es_proveedor, cedula: Same as crear_persona.

    OPTIONAL PARAMETERS:
      Same optional fields as crear_persona (minus 'origen').

    RETURNS:
      Dict with updated person data.
    """
    pos = _resolve_pos_token(pos_token)
    body: dict[str, Any] = {
        "tipo": tipo,
        "razon_social": razon_social,
        "es_cliente": es_cliente,
        "es_proveedor": es_proveedor,
        "cedula": cedula,
        "es_vendedor": es_vendedor,
        "es_empleado": es_empleado,
        "es_corporativo": es_corporativo,
        "es_extranjero": es_extranjero,
        "aplicar_cupo": aplicar_cupo,
    }
    optionals = {
        "ruc": ruc,
        "nombre_comercial": nombre_comercial,
        "email": email,
        "telefonos": telefonos,
        "direccion": direccion,
        "placa": placa,
        "porcentaje_descuento": porcentaje_descuento,
        "adicionales_cliente": adicionales_cliente,
        "adicionales_proveedor": adicionales_proveedor,
        "personaasociada_id": personaasociada_id,
        "banco_codigo_id": banco_codigo_id,
        "numero_tarjeta": numero_tarjeta,
        "tipo_cuenta": tipo_cuenta,
    }
    for k, v in optionals.items():
        if v is not None:
            body[k] = v

    result = await _request(
        "PUT",
        f"/api/v2/persona/{id_integracion}/",
        params={"pos": pos},
        body=body)
    return json.dumps(result, ensure_ascii=False, default=str)


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
    result = await _request(
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
    result = await _request("GET", f"/api/v2/categoria/{id_integracion}/")
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
    result = await _request("POST", "/api/v2/categoria/", body={"nombre": nombre})
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
    result = await _request(
        "PUT", f"/api/v2/categoria/{id_integracion}/", body={"nombre": nombre})
    return json.dumps(result, ensure_ascii=False, default=str)


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
    result = await _request(
        "GET",
        "/api/v2/bodega/",
        params={"fecha_inicial": fecha_inicial, "fecha_final": fecha_final})
    return json.dumps(result, ensure_ascii=False, default=str)


@mcp.tool()
async def obtener_bodega(    id_integracion: str
) -> str:
    """Get a warehouse by its id_integracion.

    REQUIRED PARAMETERS:
      id_integracion (str): Warehouse ID (varchar 16).

    RETURNS:
      Warehouse object with: id_integracion, nombre, codigo, venta, produccion, compra.
    """
    result = await _request("GET", f"/api/v2/bodega/{id_integracion}/")
    return json.dumps(result, ensure_ascii=False, default=str)


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
    result = await _request(
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
    return json.dumps(result, ensure_ascii=False, default=str)


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
    result = await _request("GET", f"/api/v2/producto/{id_integracion}")
    return json.dumps(result, ensure_ascii=False, default=str)


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
    for k, v in optionals.items():
        if v is not None:
            body[k] = v

    result = await _request("POST", "/api/v2/producto/", body=body)
    return json.dumps(result, ensure_ascii=False, default=str)


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
    for k, v in optionals.items():
        if v is not None:
            body[k] = v

    result = await _request("PUT", f"/api/v2/producto/{id_integracion}", body=body)
    return json.dumps(result, ensure_ascii=False, default=str)


@mcp.tool()
async def obtener_stock_producto(    id_integracion: str
) -> str:
    """Get the stock breakdown by warehouse for a specific product.

    REQUIRED PARAMETERS:
      id_integracion (str): Product ID (varchar 16).

    RETURNS:
      List of stock entries per warehouse: bodega_nombre, bodega_id, cantidad.
    """
    result = await _request("GET", f"/api/v2/producto/{id_integracion}/stock/")
    return json.dumps(result, ensure_ascii=False, default=str)


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
    result = await _request(
        "GET",
        "/api/v2/movimiento-inventario/",
        params={
            "fecha_inicial": fecha_inicial,
            "fecha_final": fecha_final,
            "estado": estado,
            "tipo": tipo,
            "bodega_id": bodega_id,
        })
    return json.dumps(result, ensure_ascii=False, default=str)


@mcp.tool()
async def obtener_movimiento_inventario(    id_integracion: str
) -> str:
    """Get an inventory movement by its id_integracion.

    REQUIRED PARAMETERS:
      id_integracion (str): Inventory movement ID (varchar 16).

    RETURNS:
      Full movement object with detalles (product_id, cantidad, precio).
    """
    result = await _request("GET", f"/api/v2/movimiento-inventario/{id_integracion}")
    return json.dumps(result, ensure_ascii=False, default=str)


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

    result = await _request("POST", "/api/v2/movimiento-inventario/", body=body)
    return json.dumps(result, ensure_ascii=False, default=str)


# ═══════════════════════════════════════════════════════════════════════════
# DOCUMENTOS  –  /api/v2/documento/
# ═══════════════════════════════════════════════════════════════════════════


@mcp.tool()
async def listar_documentos(    tipo_registro: str | None = None,
    tipo: str | None = None,
    fecha_modificacion: str | None = None,
    fecha_emision: str | None = None,
    fecha_vencimiento: str | None = None,
    fecha_creacion: str | None = None,
    persona_identificacion: str | None = None,
    page: str | None = None,
    result_page: int | None = None,
    result_size: int = 50,
    fecha_inicial: str | None = None,
    fecha_final: str | None = None,
    persona_id: str | None = None,
    bodega_id: str | None = None) -> str:
    """List and filter documents (invoices, credit notes, quotations, etc.) in Contifico.

    OPTIONAL PARAMETERS:
      tipo_registro (str): Party type filter. Valid values: "CLI"=Customer | "PRO"=Supplier
      tipo (str): Document type. Valid values:
                  "FAC"=Invoice, "LQC"=Purchase settlement, "PRE"=Pre-invoice,
                  "NCT"=Credit note, "COT"=Quotation, "OCV"=Purchase/Sale order,
                  "NVE"=Sales note, "DNA"=Non-authorized document.
      fecha_modificacion (str): Modified on date, format DD/MM/YYYY.
      fecha_emision (str): Issue date, format DD/MM/YYYY.
      fecha_vencimiento (str): Due date, format DD/MM/YYYY.
      fecha_creacion (str): Creation date, format DD/MM/YYYY.
      persona_identificacion (str): Customer/supplier cedula or RUC.
      page (str): Page number for pagination. Essential to avoid truncation. Example: "2". Default is 1.
      result_page (int): Same as page. Backwards compatibility for older prompts.
      result_size (int): Number of results per page. Default is 50. Max 100.
      fecha_inicial, fecha_final (str): Issue date range, format DD/MM/YYYY.
      persona_id (str): Person integration ID filter.
      bodega_id (str): Warehouse filter.

    RETURNS:
      Paginated list of document objects with: id_integracion, tipo_documento,
      documento (number), fecha_emision, total, estado, persona data.
    """
    # Support 'page' parameter for generic pagination
    result_page_val = result_page
    if page is not None and str(page).isdigit():
        result_page_val = int(page)

    result = await _request(
        "GET",
        "/api/v2/documento/",
        params={
            "tipo_registro": tipo_registro,
            "tipo": tipo,
            "fecha_modificacion": fecha_modificacion,
            "fecha_emision": fecha_emision,
            "fecha_vencimiento": fecha_vencimiento,
            "fecha_creacion": fecha_creacion,
            "persona_identificacion": persona_identificacion,
            "result_size": result_size,
            "result_page": result_page_val,
            "fecha_inicial": fecha_inicial,
            "fecha_final": fecha_final,
            "persona_id": persona_id,
            "bodega_id": bodega_id,
        })
    return json.dumps(result, ensure_ascii=False, default=str)


@mcp.tool()
async def crear_documento(    pos: str,
    fecha_emision: str,
    tipo_documento: str,
    tipo_registro: str,
    documento: str,
    autorizacion: str,
    descripcion: str,
    referencia: str,
    subtotal_0: float,
    subtotal_12: float,
    iva: float,
    ice: float,
    total: float,
    detalles: list[dict[str, Any]],
    cliente: dict[str, Any] | None = None,
    persona: dict[str, Any] | None = None,
    vendedor: dict[str, Any] | None = None,
    cobros: list[dict[str, Any]] | None = None,
    estado: str | None = None,
    caja_id: str | None = None,
    servicio: float | None = None,
    adicional1: str | None = None,
    adicional2: str | None = None,
    hora_emision: str | None = None,
    electronico: bool | None = None,
    documento_relacionado_id: str | None = None) -> str:
    """⚠️ MUTATION — Create a document (invoice, credit note, quotation, etc.) in Contifico — POST /api/v2/documento/.

    REQUIRED PARAMETERS:
      pos (str): POS API Token (CONTIFICO_POS_TOKEN). VARCHAR 36.
      fecha_emision (str): Issue date in DD/MM/YYYY format. Example: "30/07/2025"
      tipo_documento (str): Document type. Valid values:
                             "FAC", "LQC", "PRE", "NCT", "COT", "OCV", "NVE", "DNA"
      tipo_registro (str): Party type. Valid values: "CLI"=Customer | "PRO"=Supplier
      documento (str): Document number, varchar 17. Example: "001-001-000008089"
      autorizacion (str): SRI authorization number (varchar 49).
      descripcion (str): Document description.
      referencia (str): Reference data (additional identifier).
      subtotal_0 (float): Subtotal with 0% VAT (8 int + 2 dec).
      subtotal_12 (float): Subtotal with applicable VAT (8 int + 2 dec).
      iva (float): Total VAT amount.
      ice (float): ICE tax amount.
      total (float): Document total (8 int + 2 dec).
      detalles (list[dict]): Line items. Each requires:
                             {"producto_id": "...",          # varchar 16
                              "cantidad": 2.0,                # 7+6 decimals
                              "precio": 10.50,               # 7+6 decimals
                              "porcentaje_descuento": 0,
                              "base_cero": 0.0,
                              "base_gravable": 10.50,
                              "base_no_gravable": 0.0}

    OPTIONAL PARAMETERS:
      cliente (dict): Customer person object (for tipo_registro=CLI).
      persona (dict): Supplier person object (for tipo_registro=PRO).
      vendedor (dict): Salesperson person object.
      cobros (list[dict]): Collections: [{"forma_cobro": "EF", "monto": 11.50, "tipo_ping": null}]
      estado (str): Document status: "P"=Pending, "C"=Collected.
      caja_id (str): Cash register ID.
      servicio (float): Service charge.
      adicional1, adicional2 (str): Additional text fields.
      hora_emision (str): Emission time.
      electronico (bool): Electronic document flag.
      documento_relacionado_id (str): Related document ID (REQUIRED for NCT type).

    RETURNS:
      Dict with created document id_integracion and all fields.
    """
    body: dict[str, Any] = {
        "pos": pos,
        "fecha_emision": fecha_emision,
        "tipo_documento": tipo_documento,
        "tipo_registro": tipo_registro,
        "documento": documento,
        "autorizacion": autorizacion,
        "descripcion": descripcion,
        "referencia": referencia,
        "subtotal_0": subtotal_0,
        "subtotal_12": subtotal_12,
        "iva": iva,
        "ice": ice,
        "total": total,
        "detalles": detalles,
    }
    optionals = {
        "cliente": cliente,
        "persona": persona,
        "vendedor": vendedor,
        "cobros": cobros,
        "estado": estado,
        "caja_id": caja_id,
        "servicio": servicio,
        "adicional1": adicional1,
        "adicional2": adicional2,
        "hora_emision": hora_emision,
        "electronico": electronico,
        "documento_relacionado_id": documento_relacionado_id,
    }
    for k, v in optionals.items():
        if v is not None:
            body[k] = v

    result = await _request("POST", "/api/v2/documento/", body=body)
    return json.dumps(result, ensure_ascii=False, default=str)


@mcp.tool()
async def actualizar_documento(    id_integracion: str,
    pos: str,
    fecha_emision: str,
    tipo_documento: str,
    tipo_registro: str,
    documento: str,
    autorizacion: str,
    descripcion: str,
    referencia: str,
    subtotal_0: float,
    subtotal_12: float,
    iva: float,
    ice: float,
    total: float,
    detalles: list[dict[str, Any]],
    cliente: dict[str, Any] | None = None,
    persona: dict[str, Any] | None = None,
    vendedor: dict[str, Any] | None = None,
    estado: str | None = None,
    caja_id: str | None = None,
    servicio: float | None = None,
    adicional1: str | None = None,
    adicional2: str | None = None) -> str:
    """⚠️ MUTATION — Update an existing document by id_integracion in Contifico — PUT /api/v2/documento/{id}.

    Same required fields as crear_documento, but without cobros (collections).

    REQUIRED PARAMETERS:
      id_integracion (str): Document ID to update.
      pos, fecha_emision, tipo_documento, tipo_registro, documento, autorizacion,
      descripcion, referencia, subtotal_0, subtotal_12, iva, ice, total, detalles:
      Same as crear_documento.

    OPTIONAL PARAMETERS:
      cliente, persona, vendedor, estado, caja_id, servicio, adicional1, adicional2.

    RETURNS:
      Dict with updated document data.
    """
    body: dict[str, Any] = {
        "pos": pos,
        "fecha_emision": fecha_emision,
        "tipo_documento": tipo_documento,
        "tipo_registro": tipo_registro,
        "documento": documento,
        "autorizacion": autorizacion,
        "descripcion": descripcion,
        "referencia": referencia,
        "subtotal_0": subtotal_0,
        "subtotal_12": subtotal_12,
        "iva": iva,
        "ice": ice,
        "total": total,
        "detalles": detalles,
    }
    optionals = {
        "cliente": cliente,
        "persona": persona,
        "vendedor": vendedor,
        "estado": estado,
        "caja_id": caja_id,
        "servicio": servicio,
        "adicional1": adicional1,
        "adicional2": adicional2,
    }
    for k, v in optionals.items():
        if v is not None:
            body[k] = v

    result = await _request(
        "PUT", f"/api/v2/documento/{id_integracion}", body=body)
    return json.dumps(result, ensure_ascii=False, default=str)


@mcp.tool()
async def obtener_estado_documento(    id_integracion: str
) -> str:
    """Check the SRI authorization status of an electronic document.

    REQUIRED PARAMETERS:
      id_integracion (str): Document ID (varchar 16).

    RETURNS:
      Dict with: documento_id, tipo_registro, tipo_documento, estado.
      estado values: "Firmado" | "Enviado a SRI" | "Autorizado" | "No Firmado"
    """
    result = await _request(
        "GET", f"/api/v2/documento/estado/{id_integracion}")
    return json.dumps(result, ensure_ascii=False, default=str)


# ═══════════════════════════════════════════════════════════════════════════
# COBROS  –  /api/v2/documento/{id}/cobro/
# ═══════════════════════════════════════════════════════════════════════════


@mcp.tool()
async def listar_cobros_documento(    id_integracion: str
) -> str:
    """List all collections (cobros) for a customer document.

    REQUIRED PARAMETERS:
      id_integracion (str): Document ID (varchar 16). Must be a customer document.

    RETURNS:
      List of collection objects with: forma_cobro, monto, tipo_ping, fecha.
    """
    result = await _request(
        "GET", f"/api/v2/documento/{id_integracion}/cobro/")
    return json.dumps(result, ensure_ascii=False, default=str)


@mcp.tool()
async def crear_cobro_documento(    id_integracion: str,
    forma_cobro: str,
    monto: float,
    tipo_ping: str | None = None,
    fecha: str | None = None,
    numero_cheque: str | None = None,
    cuenta_bancaria_id: str | None = None,
    numero_comprobante: str | None = None,
    lote: str | None = None) -> str:
    """⚠️ MUTATION — Register a payment collection on an existing document — POST /api/v2/documento/{id}/cobro/.

    REQUIRED PARAMETERS:
      id_integracion (str): Document ID to add the collection to (varchar 16).
      forma_cobro (str): Payment method code. Valid values:
                         "EF"=Cash | "CQ"=Check | "TC"=Credit card | "TRA"=Transfer
      monto (float): Amount collected (8 int + 2 dec).

    CONDITIONAL PARAMETERS:
      tipo_ping (str): REQUIRED when forma_cobro="TC". Card processor code:
                       "D"=Datafast | "M"=Medianet | "E"=Dataexpress |
                       "P"=Placetopay | "A"=Alignet

    OPTIONAL PARAMETERS:
      fecha (str): Collection date, format DD/MM/YYYY.
      numero_cheque (str): Check number (for forma_cobro=CQ, varchar 15).
      cuenta_bancaria_id (str): Bank account ID receiving the payment (varchar 16).
      numero_comprobante (str): Sequence/voucher number (varchar 15).
      lote (str): Batch identifier.

    RETURNS:
      Dict with created collection id and confirmation.
    """
    body: dict[str, Any] = {
        "forma_cobro": forma_cobro,
        "monto": monto,
    }
    optionals = {
        "tipo_ping": tipo_ping,
        "fecha": fecha,
        "numero_cheque": numero_cheque,
        "cuenta_bancaria_id": cuenta_bancaria_id,
        "numero_comprobante": numero_comprobante,
        "lote": lote,
    }
    for k, v in optionals.items():
        if v is not None:
            body[k] = v

    result = await _request(
        "POST", f"/api/v2/documento/{id_integracion}/cobro/", body=body)
    return json.dumps(result, ensure_ascii=False, default=str)


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
    result = await _request("GET", "/api/v2/banco/cuenta/")
    return json.dumps(result, ensure_ascii=False, default=str)


@mcp.tool()
async def obtener_cuenta_bancaria(    id_integracion: str
) -> str:
    """Get a bank account by its id_integracion.

    REQUIRED PARAMETERS:
      id_integracion (str): Bank account ID (varchar 16).

    RETURNS:
      Bank account object with all fields.
    """
    result = await _request("GET", f"/api/v2/banco/cuenta/{id_integracion}/")
    return json.dumps(result, ensure_ascii=False, default=str)


# ═══════════════════════════════════════════════════════════════════════════
# FORMAS DE PAGO  –  /api/v2/documento/{id}/forma_pago
# ═══════════════════════════════════════════════════════════════════════════


@mcp.tool()
async def obtener_formas_pago_documento(    id_integracion: str
) -> str:
    """Get the payment methods configured for a specific document.

    REQUIRED PARAMETERS:
      id_integracion (str): Document ID (varchar 16).

    RETURNS:
      List of payment method objects: forma_pago, plazo, unidad, valor.
    """
    result = await _request(
        "GET", f"/api/v2/documento/{id_integracion}/forma_pago")
    return json.dumps(result, ensure_ascii=False, default=str)


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
    result = await _request("GET", "/api/v2/empresa/parametros")
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
    result = await _request("GET", "/api/v2/unidad/")
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
    result = await _request("GET", f"/api/v2/unidad/{id_integracion}")
    return json.dumps(result, ensure_ascii=False, default=str)


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
    result = await _request(
        "GET",
        "/api/v2/contabilidad/asiento/",
        params={
            "page": page,
            "fecha_inicial": fecha_inicial,
            "fecha_final": fecha_final,
            "centro_costo": centro_costo,
        })
    return json.dumps(result, ensure_ascii=False, default=str)


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
    result = await _request(
        "GET", f"/api/v2/contabilidad/asiento/{id_integracion}")
    return json.dumps(result, ensure_ascii=False, default=str)


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
    result = await _request("GET", "/api/v1/contabilidad/cuenta-contable/", params=params)
    return json.dumps(result, ensure_ascii=False, default=str)


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
    result = await _request("GET", "/api/v1/contabilidad/centro-costo/", params=params)
    return json.dumps(result, ensure_ascii=False, default=str)


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
    result = await _request("POST", "/api/v1/contabilidad/asiento/", body=payload, params=params)
    return json.dumps(result, ensure_ascii=False, default=str)


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

    result = await _request("GET", "/api/v1/banco/movimiento/", params=params if params else None)
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
    result = await _request("GET", "/api/v1/rrhh/rol/", params=params)
    return json.dumps(result, ensure_ascii=False, default=str)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    import uvicorn
    import os

    try:
        import logger
    except ImportError:
        pass

    port = int(os.getenv("MCP_PORT", 8000))
    transport_mode = os.getenv("MCP_TRANSPORT_MODE", "sse").lower()
    print(f"Starting MCP Server on http://0.0.0.0:{port}/mcp ({transport_mode})")
    if transport_mode == "sse":
        app = mcp.sse_app()
    elif transport_mode == "http_stream":
        app = mcp.streamable_http_app()
    else:
        raise ValueError(f"Unknown transport mode: {transport_mode}")
    uvicorn.run(app, host="0.0.0.0", port=port)
