# Odoo 18 MCP Server

Servidor MCP (Model Context Protocol) para conectar Claude con instancias de Odoo 18 a través de XML-RPC.

## Herramientas disponibles

| Herramienta | Descripción |
|---|---|
| `test_connection` | Verificar conexión con Odoo |
| `list_models` | Listar modelos disponibles |
| `get_model_fields` | Ver campos de un modelo |
| `search_records` | Buscar registros con filtros de dominio |
| `read_record` | Leer un registro por ID |
| `create_record` | Crear un nuevo registro |
| `update_record` | Actualizar un registro existente |
| `delete_record` | Eliminar un registro |
| `count_records` | Contar registros |
| `search_by_name` | Buscar por nombre |
| `execute_method` | Ejecutar métodos personalizados de modelos |
| `search_partner` | Buscar contactos (atajo) |
| `get_sales_orders` | Consultar órdenes de venta |
| `get_invoices` | Consultar facturas |
| `get_products` | Consultar productos |

## Requisitos

- Python 3.10+
- Instancia de Odoo 18 con XML-RPC habilitado (habilitado por defecto)

## Instalación

```bash
# Con uv (recomendado)
uv pip install -e .

# Con pip
pip install -e .
```

## Configuración

Copia `.env.example` a `.env` y configura tus credenciales:

```bash
cp .env.example .env
```

```env
ODOO_URL=http://localhost:8069
ODOO_DB=odoo18
ODOO_USERNAME=admin
ODOO_PASSWORD=admin
```

O usa API key (alternativa a usuario/contraseña):

```env
ODOO_URL=http://localhost:8069
ODOO_DB=odoo18
ODOO_API_KEY=tu-api-key
```

## Uso con Claude Desktop

Agrega la configuración en `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "odoo18": {
      "command": "uv",
      "args": [
        "--directory",
        "/ruta/absoluta/al/proyecto",
        "run",
        "odoo18-mcp-server"
      ],
      "env": {
        "ODOO_URL": "http://localhost:8069",
        "ODOO_DB": "odoo18",
        "ODOO_USERNAME": "admin",
        "ODOO_PASSWORD": "admin"
      }
    }
  }
}
```

## Uso con Claude Code

```bash
claude mcp add odoo18 -- uv --directory /ruta/al/proyecto run odoo18-mcp-server
```

O con variables de entorno:

```bash
claude mcp add odoo18 \
  -e ODOO_URL=http://localhost:8069 \
  -e ODOO_DB=odoo18 \
  -e ODOO_USERNAME=admin \
  -e ODOO_PASSWORD=admin \
  -- uv --directory /ruta/al/proyecto run odoo18-mcp-server
```

## Ejemplos de uso (desde Claude)

### Buscar contactos
> "Busca todos los contactos que sean empresas"

Claude usará `search_partner` con `is_company=True`.

### Consultar ventas
> "Muéstrame las órdenes de venta en estado borrador"

Claude usará `get_sales_orders` con `state="draft"`.

### Explorar un modelo
> "Quiero ver la estructura del modelo stock.picking"

Claude usará `get_model_fields` con `model="stock.picking"`.

### Crear un contacto
> "Crea un nuevo contacto llamado Juan Pérez con email juan@example.com"

Claude usará `create_record` en `res.partner`.

### Dominio avanzado
> "Busca facturas publicadas del cliente Acme con monto mayor a 1000"

Claude usará `search_records` en `account.move` con dominio:
```json
[["state","=","posted"],["partner_id.name","ilike","Acme"],["amount_total",">",1000]]
```

## Desarrollo

```bash
# Instalar en modo desarrollo
uv pip install -e ".[dev]"

# Probar con el inspector MCP
uv run mcp dev src/odoo_mcp/server.py

# Ejecutar directamente
uv run odoo18-mcp-server
```

## Estructura del proyecto

```
├── pyproject.toml              # Configuración del proyecto
├── .env.example                # Plantilla de variables de entorno
├── .gitignore
├── README.md
└── src/
    └── odoo_mcp/
        ├── __init__.py
        ├── config.py           # Gestión de configuración
        ├── odoo_client.py      # Cliente XML-RPC para Odoo
        └── server.py           # Servidor MCP con todas las herramientas
```

## Licencia

MIT
