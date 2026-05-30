"""FastMCP application instance for the Contifico MCP server.

Split out of server.py (issue #1) verbatim.
"""
import os

from mcp.server.fastmcp import FastMCP


mcp = FastMCP(
    "contifico",
    host=os.getenv("MCP_HOST", "0.0.0.0"),  # nosec B104 — configurable via MCP_HOST env
    instructions=(
        "MCP server for Contifico REST API v2 — cloud accounting system for Ecuador. "
        "Manages: people (customers/suppliers/employees), products, documents (invoices, "
        "credit notes, quotations), categories, warehouses, inventory movements, "
        "collections, bank accounts, payment methods, accounting entries, and payroll. "
        "Credentials are read per request from the 'Authorization: Bearer <key>' header "
        "(multi-tenant); CONTIFICO_API_KEY env var is a local-dev-only fallback. "
        "WRITE OPERATIONS: crear_persona and actualizar_persona also require `pos_token`. "
        "PAGINATION: listar_* tools return 100 results per page. Use 'page' parameter to paginate. "
        "DATE FORMAT: All date fields use DD/MM/YYYY format. Example: '30/07/2025'. To filter documents by issue date, use 'fecha_inicial' and 'fecha_final' instead of generic date fields. "
        "DOCUMENT TYPES: FAC=Invoice, LQC=Purchase settlement, PRE=Pre-invoice, "
        "NCT=Credit note, COT=Quotation, OCV=Purchase/Sale order, NVE=Sales note. "
        "PERSON TYPES: N=Natural, J=Legal entity, I=No ID (needs personaasociada_id), P=Plate. "
        "INVENTORY TYPES: ING=Entry, EGR=Exit, TRA=Transfer (requires bodega_destino_id)."
    ))
