"""Contifico MCP tools: personas.

Split out of server.py (issue #1). Tool bodies are verbatim except that
request helpers are called through the ``server`` module (server._request
/ server._resolve_pos_token) so the test suite's monkeypatching works.
"""
import json
from typing import Any

import server
from app import mcp


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
    result = await server._request(
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
    result = await server._request("GET", f"/api/v2/persona/{id_integracion}/")
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
    pos = server._resolve_pos_token(pos_token)
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

    result = await server._request(
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
    pos = server._resolve_pos_token(pos_token)
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

    result = await server._request(
        "PUT",
        f"/api/v2/persona/{id_integracion}/",
        params={"pos": pos},
        body=body)
    return json.dumps(result, ensure_ascii=False, default=str)
