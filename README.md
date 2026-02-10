# Odoo 18 MCP Server

Servidor MCP (Model Context Protocol) para conectar Claude con instancias de Odoo 18 a través de XML-RPC.

## Herramientas disponibles (37 tools)

### General / CRUD

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
| `bulk_create_records` | Crear múltiples registros a la vez |
| `bulk_update_records` | Actualizar múltiples registros a la vez |
| `get_default_values` | Obtener valores por defecto de un modelo |
| `read_group_data` | Datos agrupados/agregados (GROUP BY) |

### CRM

| Herramienta | Descripción |
|---|---|
| `get_leads` | Consultar leads y oportunidades |
| `get_crm_pipeline_summary` | Resumen del pipeline CRM por etapa |

### Ventas

| Herramienta | Descripción |
|---|---|
| `search_partner` | Buscar contactos (atajo) |
| `get_sales_orders` | Consultar órdenes de venta |
| `get_sale_order_lines` | Consultar líneas de órdenes de venta |
| `get_products` | Consultar productos |
| `get_sales_summary` | Resumen de ventas agrupado por dimensión |
| `get_pos_orders` | Consultar órdenes de punto de venta |

### Compras

| Herramienta | Descripción |
|---|---|
| `get_purchase_orders` | Consultar órdenes de compra |

### Inventario / Almacén

| Herramienta | Descripción |
|---|---|
| `get_stock_pickings` | Consultar transferencias (recepciones, envíos) |
| `get_stock_quants` | Consultar niveles de stock por ubicación |
| `get_stock_moves` | Consultar movimientos de stock |
| `get_warehouses` | Listar almacenes |

### Contabilidad / Finanzas

| Herramienta | Descripción |
|---|---|
| `get_invoices` | Consultar facturas y notas de crédito |
| `get_invoice_lines` | Consultar líneas de factura |
| `get_payments` | Consultar pagos |
| `get_journal_entries` | Consultar asientos contables |
| `get_journal_items` | Consultar apuntes contables (líneas) |
| `get_account_balances` | Saldos de cuentas (balance de comprobación) |
| `get_contacts_with_overdue_invoices` | Contactos con facturas vencidas |

### Recursos Humanos

| Herramienta | Descripción |
|---|---|
| `get_employees` | Consultar empleados |
| `get_departments` | Listar departamentos |
| `get_leaves` | Consultar solicitudes de ausencia |

### Proyectos

| Herramienta | Descripción |
|---|---|
| `get_projects` | Consultar proyectos |
| `get_tasks` | Consultar tareas de proyecto |

### Manufactura

| Herramienta | Descripción |
|---|---|
| `get_manufacturing_orders` | Consultar órdenes de producción |
| `get_bill_of_materials` | Consultar listas de materiales (BoM) |

### Utilidades

| Herramienta | Descripción |
|---|---|
| `get_company_info` | Información de la empresa actual |
| `get_users` | Listar usuarios del sistema |
| `get_chatter_messages` | Mensajes del chatter de un registro |
| `get_activities` | Actividades programadas (pendientes, vencidas) |
| `get_installed_modules` | Listar módulos instalados |

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

### Ver pipeline CRM
> "Dame un resumen del pipeline de ventas"

Claude usará `get_crm_pipeline_summary`.

### Consultar stock
> "Cuántas unidades hay del producto 'Laptop Pro' en todos los almacenes?"

Claude usará `get_stock_quants` con `product_name="Laptop Pro"`.

### Facturas vencidas
> "Qué clientes tienen facturas vencidas?"

Claude usará `get_contacts_with_overdue_invoices`.

### Actividades pendientes
> "Muéstrame las actividades vencidas"

Claude usará `get_activities` con `overdue_only=True`.

### Resumen de ventas por vendedor
> "Dame un resumen de ventas por vendedor del último mes"

Claude usará `get_sales_summary` con `group_by="user_id"` y filtros de fecha.

### Crear múltiples contactos
> "Crea estos 3 proveedores: Proveedor A, Proveedor B, Proveedor C"

Claude usará `bulk_create_records` en `res.partner`.

### Dominio avanzado
> "Busca facturas publicadas del cliente Acme con monto mayor a 1000"

Claude usará `search_records` en `account.move` con dominio:
```json
[["state","=","posted"],["partner_id.name","ilike","Acme"],["amount_total",">",1000]]
```

### Analítica con agrupación
> "Cuántas órdenes de producción hay por estado?"

Claude usará `read_group_data` en `mrp.production` con `groupby="state"`.

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
