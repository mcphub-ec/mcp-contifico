# MCP Server — Contifico API v2

Servidor [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) que expone los servicios de la API REST v2 de **Contifico** como herramientas invocables por un agente de IA.

Contifico es un sistema contable en la nube ampliamente utilizado en **Ecuador** para facturación electrónica, inventario y contabilidad.

---

## Herramientas expuestas

| Módulo | Tools | Operaciones |
|---|---|---|
| **Personas** | `listar_personas`, `obtener_persona`, `crear_persona`, `actualizar_persona` | CRUD clientes, proveedores, empleados |
| **Categorías** | `listar_categorias`, `obtener_categoria`, `crear_categoria`, `actualizar_categoria` | CRUD categorías de productos |
| **Bodegas** | `listar_bodegas`, `obtener_bodega` | Consulta de bodegas |
| **Productos** | `listar_productos`, `obtener_producto`, `crear_producto`, `actualizar_producto`, `obtener_stock_producto` | CRUD productos + stock por bodega |
| **Mov. Inventario** | `listar_movimientos_inventario`, `obtener_movimiento_inventario`, `crear_movimiento_inventario` | Ingreso, egreso, traslado |
| **Documentos** | `listar_documentos`, `crear_documento`, `actualizar_documento`, `obtener_estado_documento` | Facturas, NCT, Prefacturas, etc. |
| **Cobros** | `listar_cobros_documento`, `crear_cobro_documento` | Efectivo, TC, transferencia, cheque |
| **Cuentas Bancarias** | `listar_cuentas_bancarias`, `obtener_cuenta_bancaria` | Consulta de cuentas |
| **Formas de Pago** | `obtener_formas_pago_documento` | Consulta formas de pago |
| **Parámetros** | `obtener_parametros_empresa` | Parámetros de empresa |
| **Unidades** | `listar_unidades`, `obtener_unidad` | Unidades de medida |
| **Asientos** | `listar_asientos`, `obtener_asiento` | Consulta asientos contables |

---

## Requisitos previos

- **Sistema operativo:** Debian 12+ / Ubuntu 22.04+ (o cualquier LXC con systemd).
- **Python:** 3.11 o superior.
- **Paquetes del sistema:** `python3-venv`, `python3-pip`.
- **Credenciales Contifico:** `API_KEY` y `POS Token` (solicitar al soporte de Contifico).

---

## Instalación paso a paso

### 1. Preparar el sistema

```bash
sudo apt update && sudo apt install -y python3 python3-venv python3-pip git
```

### 2. Clonar el repositorio

```bash
git clone <URL_DEL_REPOSITORIO> /opt/mcp-contifico
cd /opt/mcp-contifico
```

### 3. Crear entorno virtual e instalar dependencias

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install "mcp[cli]" httpx
```

### 4. Configurar las variables de entorno

Crea un archivo `.env` en el directorio raíz del proyecto:

```bash
cat > .env << 'EOF'
CONTIFICO_API_KEY=TU_API_KEY_AQUI
CONTIFICO_POS_TOKEN=TU_POS_TOKEN_AQUI
CONTIFICO_BASE_URL=https://api.contifico.com/sistema
CONTIFICO_HTTP_TIMEOUT=30
EOF
chmod 600 .env
```

> **⚠️ Importante:** Nunca versiones el archivo `.env`. Asegúrate de que esté en `.gitignore`.

### 5. Verificar la instalación

```bash
source .venv/bin/activate
source .env
python server.py
```

El servidor arrancará en modo `stdio` y quedará esperando mensajes MCP por stdin.

---

## Ejecución

### Modo stdio (uso con agente)

```bash
source .venv/bin/activate
export $(grep -v '^#' .env | xargs)
python server.py
```

### Modo inspector (debug)

```bash
source .venv/bin/activate
export $(grep -v '^#' .env | xargs)
mcp dev server.py
```

Esto levanta el MCP Inspector en `http://localhost:5173` para probar las herramientas interactivamente.

---

## Integración con clientes MCP

### Claude Desktop

Agrega esta configuración al archivo `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "contifico": {
      "command": "/opt/mcp-contifico/.venv/bin/python",
      "args": ["/opt/mcp-contifico/server.py"],
      "env": {
        "CONTIFICO_API_KEY": "TU_API_KEY_AQUI",
        "CONTIFICO_POS_TOKEN": "TU_POS_TOKEN_AQUI"
      }
    }
  }
}
```

### Cursor / Windsurf / VS Code (Copilot)

Crea un archivo `.mcp.json` en la raíz del proyecto:

```json
{
  "servers": {
    "contifico": {
      "command": "/opt/mcp-contifico/.venv/bin/python",
      "args": ["/opt/mcp-contifico/server.py"],
      "env": {
        "CONTIFICO_API_KEY": "TU_API_KEY_AQUI",
        "CONTIFICO_POS_TOKEN": "TU_POS_TOKEN_AQUI"
      }
    }
  }
}
```

---

## Servicio systemd (producción)

Para mantener el servidor activo como un servicio del sistema:

```bash
sudo cat > /etc/systemd/system/mcp-contifico.service << 'EOF'
[Unit]
Description=MCP Server - Contifico API v2
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/mcp-contifico
EnvironmentFile=/opt/mcp-contifico/.env
ExecStart=/opt/mcp-contifico/.venv/bin/python /opt/mcp-contifico/server.py
Restart=on-failure
RestartSec=5
StandardInput=null
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now mcp-contifico
sudo systemctl status mcp-contifico
```

---

## Variables de entorno

| Variable | Obligatoria | Descripción |
|---|---|---|
| `CONTIFICO_API_KEY` | ✅ | API Key proporcionada por Contifico (header `Authorization`). |
| `CONTIFICO_POS_TOKEN` | ✅* | Token del POS. Requerido para operaciones de escritura (crear persona, documentos). |
| `CONTIFICO_BASE_URL` | ❌ | URL base de la API. Default: `https://api.contifico.com/sistema`. |
| `CONTIFICO_HTTP_TIMEOUT` | ❌ | Timeout en segundos para las peticiones HTTP. Default: `30`. |

---

## Estructura del proyecto

```
/opt/mcp-contifico/
├── server.py            # Servidor MCP principal
├── .env                 # Variables de entorno (NO versionar)
├── .env.example         # Plantilla de variables de entorno
├── README.md            # Este archivo
└── docs/
    └── openapiv2.yaml   # Especificación OpenAPI v2 de Contifico (fuente de verdad)
```

---

## Referencia rápida de tipos de documento

| Código | Tipo |
|---|---|
| `FAC` | Factura |
| `LQC` | Liquidación de Compra |
| `PRE` | Prefactura |
| `NCT` | Nota de Crédito |
| `COT` | Cotización |
| `OCV` | Orden de Compra/Venta |
| `NVE` | Nota de Venta |
| `DNA` | Documento No Autorizado |

## Referencia rápida de formas de cobro

| Código | Forma |
|---|---|
| `EF` | Efectivo |
| `CQ` | Cheque |
| `TC` | Tarjeta de Crédito |
| `TRA` | Transferencia |

## Referencia rápida de tipos de persona

| Código | Tipo |
|---|---|
| `N` | Natural |
| `J` | Jurídica |
| `I` | Sin ID (requiere `personaasociada_id`) |
| `P` | Placa |

---

## Licencia

MIT
# mcp-contifico
