"""Contifico MCP tools: documentos.

Split out of server.py (issue #1). Tool bodies are verbatim except that
request helpers are called through the ``server`` module (server._request
/ server._resolve_pos_token) so the test suite's monkeypatching works.
"""
import json
from typing import Any

import server
from app import mcp


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

    result = await server._request(
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
    return server._json(result)


@mcp.tool()
async def crear_documento(    fecha_emision: str,
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
    pos: str | None = None,
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
    documento_relacionado_id: str | None = None,
    reserva_relacionada: str | None = None) -> str:
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
      reserva_relacionada (str): ID of a related reservation (optional, for accounts
                                  using the reservations module). Send null if not applicable.

    RETURNS:
      Dict with created document id_integracion and all fields.
    """
    resolved_pos = server._resolve_pos_token(pos or "")

    body: dict[str, Any] = {
        "pos": resolved_pos,
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
        "reserva_relacionada": reserva_relacionada,
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
    body.update(server._drop_none(optionals))

    result = await server._request("POST", "/api/v2/documento/", body=body)
    return server._json(result)


@mcp.tool()
async def actualizar_documento(    id_integracion: str,
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
    pos: str | None = None,
    cliente: dict[str, Any] | None = None,
    persona: dict[str, Any] | None = None,
    vendedor: dict[str, Any] | None = None,
    estado: str | None = None,
    caja_id: str | None = None,
    servicio: float | None = None,
    adicional1: str | None = None,
    adicional2: str | None = None,
    reserva_relacionada: str | None = None) -> str:
    """⚠️ MUTATION — Update an existing document by id_integracion in Contifico — PUT /api/v2/documento/{id}.

    Same required fields as crear_documento, but without cobros (collections).

    REQUIRED PARAMETERS:
      id_integracion (str): Document ID to update.
      pos, fecha_emision, tipo_documento, tipo_registro, documento, autorizacion,
      descripcion, referencia, subtotal_0, subtotal_12, iva, ice, total, detalles:
      Same as crear_documento.

    OPTIONAL PARAMETERS:
      cliente, persona, vendedor, estado, caja_id, servicio, adicional1, adicional2.
      reserva_relacionada (str): ID of a related reservation (optional, for accounts
                                  using the reservations module). Send null if not applicable.

    RETURNS:
      Dict with updated document data.
    """
    resolved_pos = server._resolve_pos_token(pos or "")

    body: dict[str, Any] = {
        "pos": resolved_pos,
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
        "reserva_relacionada": reserva_relacionada,
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
    body.update(server._drop_none(optionals))

    result = await server._request(
        "PUT", f"/api/v2/documento/{id_integracion}", body=body)
    return server._json(result)


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
    result = await server._request(
        "GET", f"/api/v2/documento/estado/{id_integracion}")
    return server._json(result)


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
    result = await server._request(
        "GET", f"/api/v2/documento/{id_integracion}/cobro/")
    return server._json(result)


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
    body.update(server._drop_none(optionals))

    result = await server._request(
        "POST", f"/api/v2/documento/{id_integracion}/cobro/", body=body)
    return server._json(result)


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
    result = await server._request(
        "GET", f"/api/v2/documento/{id_integracion}/forma_pago")
    return server._json(result)
