# Agent-First Documentation: Contifico MCP Server

## 1. Contexto General
Este proyecto es un servidor Model Context Protocol (MCP) que consolida la interacción con la API REST de Contifico (Ecuador) unificando los endpoints de V1 y V2.
Está construido en Python utilizando la librería `fastmcp`. Su propósito es exponer funcionalidades avanzadas como facturación, transacciones bancarias, contabilidad financiera (cuentas, centros de costo, asientos), recursos humanos e inventario (productos, personas, documentos) a los agentes de IA.

## 2. Tecnologías Principales
- **Python** con **FastMCP**: Utilizado para la creación del servidor y definición de las herramientas (`@mcp.tool()`).
- **httpx**: Cliente HTTP asíncrono para las peticiones a la API de Contifico.
- **dotenv**: Manejo de entorno.

## 3. Variables de Entorno Requeridas
El servidor utiliza las siguientes variables (verificadas en tiempo de ejecución para operaciones seguras):
- `CONTIFICO_API_KEY`: Clave de autorización para todas las peticiones a la API.
- `CONTIFICO_POS_TOKEN`: Token empleado nativamente para transacciones con origen en el punto de venta (muy recomendado al crear asientos o actualizar data).
- `CONTIFICO_BASE_URL`: URL base general (por defecto `https://api.contifico.com/sistema`).

## 4. Consideraciones Técnicas
- **Enfoque Mixto V1/V2**: El cliente centralizado `_request` direcciona hacia `/api/v2/...` para inventarios y documentos, y excepcionalmente hacia `/api/v1/...` para flujos adicionales como contabilidad pura, roles de pago y movimientos bancarios que continúan estando en v1.
- **Estandarización de Respuestas**: Las peticiones utilizan un método `_request` genérico. Toda herramienta MCP devuelve un string (`json.dumps(result, ensure_ascii=False, default=str)`) para la compatibilidad total del lado del cliente.
- **POST/PUT**: En herramientas como `crear_asiento_contable` o `crear_producto`, valida siempre los identificadores cruzados. Aportar un `pos_token` garantizará que la herramienta tenga los premisos correctos si ocurre un rechazo `401/403`.

## 5. Instrucciones para la Edición de Código
- Al agregar nuevos endpoints de Contifico, verifica primero en qué versión de API (`/api/v1/` o `/api/v2/`) corre la herramienta de acuerdo a la documentación oficial.
- Manten los docstrings nutridos definiendo los campos de entrada, esto es importante para que el agente entienda el esquema del payload.
