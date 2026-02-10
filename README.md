# Odoo 18 MCP Server

Servidor MCP (Model Context Protocol) para conectar Claude con instancias de Odoo 18 a través de XML-RPC.

## Herramientas disponibles (82 tools)

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

### PDF / Documentos

| Herramienta | Descripción |
|---|---|
| `parse_pdf` | Extraer texto y tablas de un PDF |
| `parse_pdf_and_create_vendor_bill` | Analizar PDF de factura y preparar datos para crear factura de proveedor |
| `create_vendor_bill` | Crear factura de proveedor con líneas (desde datos de un PDF) |
| `create_purchase_order_with_lines` | Crear orden de compra con líneas (desde datos de un PDF) |
| `create_sale_order_with_lines` | Crear orden de venta/cotización con líneas |
| `attach_file_to_record` | Adjuntar archivo (PDF, imagen) a un registro de Odoo |

### Petshop y Clínica Veterinaria (Black Dog)

| Herramienta | Descripción |
|---|---|
| `get_pets` | Buscar mascotas con filtros (dueño, especie, vacunación) |
| `get_pet_details` | Ver detalle completo de una mascota con historial de servicios y vacunas |
| `get_pet_breeds` | Catálogo de razas por especie |
| `get_pet_service_templates` | Plantillas de servicios (baño, corte, spa) |
| `get_pets_with_overdue_vaccines` | Mascotas con vacunas vencidas |

### Auditoría Operativa

| Herramienta | Descripción |
|---|---|
| `get_audit_logs` | Consultar logs de auditoría por tipo, severidad, estado |
| `get_audit_summary` | Resumen de auditorías abiertas por tipo y severidad |

### Control de Vencimientos

| Herramienta | Descripción |
|---|---|
| `get_expiring_products` | Productos próximos a vencer (por estado, almacén) |
| `get_expiry_summary` | Resumen de vencimientos por estado y almacén |

### Ajustes de Inventario

| Herramienta | Descripción |
|---|---|
| `get_inventory_adjustment_logs` | Logs de auditoría de ajustes de inventario |

### Transferencias entre Tiendas

| Herramienta | Descripción |
|---|---|
| `get_transfer_requests` | Solicitudes de transferencia interna (workflow de aprobación) |

### Reabastecimiento Estimado

| Herramienta | Descripción |
|---|---|
| `get_replenishment_orders` | Órdenes de reabastecimiento (tienda o almacén) |

### Metas de Ventas y Analítica

| Herramienta | Descripción |
|---|---|
| `get_sales_targets` | Metas mensuales de ventas por cuenta analítica |
| `get_sales_target_performance` | Rendimiento histórico vs metas (%, logro, crecimiento) |

### Segmentación de Clientes

| Herramienta | Descripción |
|---|---|
| `get_customer_segmentation` | Datos RFM, valor, riesgo de abandono por cliente |
| `get_customer_segmentation_summary` | Resumen por tier, segmento de valor y riesgo |

### Aprobación de Productos

| Herramienta | Descripción |
|---|---|
| `get_product_requests` | Solicitudes de creación de productos (workflow de aprobación) |

### Aprobación de Compras

| Herramienta | Descripción |
|---|---|
| `get_purchase_approval_status` | Estado de aprobación de OC por meses de inventario proyectado |

### Pasarelas de Pago (Tilopay & Yappy)

| Herramienta | Descripción |
|---|---|
| `get_tilopay_transactions` | Transacciones de pago Tilopay |
| `get_yappy_transactions` | Transacciones de pago Yappy (móvil Panamá) |

### Mensajería WhatsApp (Respond.io & Wassenger)

| Herramienta | Descripción |
|---|---|
| `get_respond_message_logs` | Logs de mensajes enviados por Respond.io |
| `get_respond_buttons` | Botones/plantillas configurados en Respond.io |
| `get_wassenger_message_logs` | Logs de mensajes WhatsApp enviados por Wassenger |

### Shopify

| Herramienta | Descripción |
|---|---|
| `get_shopify_instances` | Instancias de Shopify configuradas |
| `get_shopify_products` | Productos sincronizados con Shopify |

### Márgenes de Producto

| Herramienta | Descripción |
|---|---|
| `get_product_margins` | Márgenes de ganancia, markup y precio sugerido |

### Discrepancias de Inventario

| Herramienta | Descripción |
|---|---|
| `get_stock_discrepancies` | Discrepancias entre inventario teórico y físico |

### Comisiones de Peluqueros y Veterinarios

| Herramienta | Descripción |
|---|---|
| `get_groomer_commissions` | Líneas detalladas de comisión por peluquero (servicio, monto, % compartido) |
| `get_groomer_commission_summary` | Resumen mensual de comisiones con KPIs, sanciones y monto final |
| `get_vet_commission_summary` | Resumen mensual de comisiones de veterinarios |
| `get_groomer_sanctions` | Sanciones de peluqueros (ausencias, tardanzas, quejas) |

### Mascotas por Comercial

| Herramienta | Descripción |
|---|---|
| `get_pets_per_salesperson` | Cantidad de mascotas atendidas por vendedor/comercial |
| `get_pet_service_lines_by_commercial` | Resumen de órdenes con mascotas agrupado por comercial |
| `get_pet_comanda_details` | Comandas detalladas de mascotas con peluqueros asignados y estado |

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

### Procesar factura de proveedor desde PDF
> "Tengo esta factura en PDF, créala como factura de proveedor en Odoo"
> (le proporcionas la ruta al archivo PDF)

Claude realizará:
1. `parse_pdf_and_create_vendor_bill` para extraer texto y tablas del PDF
2. Analizará los datos (proveedor, fecha, líneas, montos)
3. `create_vendor_bill` con los datos extraídos
4. `attach_file_to_record` para adjuntar el PDF original al registro

### Crear orden de compra desde un PDF
> "Procesa este PDF como orden de compra: /tmp/orden_compra.pdf"

Claude realizará:
1. `parse_pdf` para leer el documento
2. Identificará proveedor, productos, cantidades y precios
3. `create_purchase_order_with_lines` para crear la OC en Odoo
4. `attach_file_to_record` para adjuntar el original

### Leer contenido de cualquier PDF
> "Qué dice este PDF? /home/user/documento.pdf"

Claude usará `parse_pdf` y te mostrará el texto, tablas y montos detectados.

### Ver mascotas de un cliente
> "Muéstrame las mascotas de Juan Pérez con su historial de vacunas"

Claude usará `get_pets` con `owner_name="Juan Pérez"` y luego `get_pet_details` para cada mascota.

### Mascotas con vacunas vencidas
> "Qué mascotas necesitan vacunación?"

Claude usará `get_pets_with_overdue_vaccines`.

### Alertas de auditoría
> "Hay alertas críticas de auditoría abiertas?"

Claude usará `get_audit_logs` con `severity="critical"` y `state="open"`.

### Productos por vencer
> "Qué productos están por vencer en los próximos 30 días?"

Claude usará `get_expiring_products` con `state="one_month"` y `handled=False`.

### Rendimiento de ventas vs metas
> "Cómo vamos con las metas de ventas de enero 2025?"

Claude usará `get_sales_target_performance` con `month="1"` y `year=2025`.

### Clientes en riesgo de abandono
> "Qué clientes VIP están en riesgo de irse?"

Claude usará `get_customer_segmentation` con `value_segment="vip"` y `churn_risk="alto"`.

### Solicitudes de productos pendientes
> "Hay productos esperando aprobación?"

Claude usará `get_product_requests` con `state="to_approve"`.

### Transacciones Yappy
> "Muéstrame las transacciones de Yappy pendientes"

Claude usará `get_yappy_transactions` con `state="pending"`.

### Comisiones de peluqueros
> "Cuánto ganó cada peluquero en enero 2025?"

Claude usará `get_groomer_commission_summary` con `year="2025"` y filtrando por mes.

### Comisiones detalladas de un peluquero
> "Muéstrame los servicios y comisiones de María en febrero"

Claude usará `get_groomer_commissions` con `groomer_name="María"` y `month="Febrero"`.

### Sanciones de peluqueros
> "Qué sanciones tiene Pedro este mes?"

Claude usará `get_groomer_sanctions` con `groomer_name="Pedro"` y filtros de fecha.

### Mascotas por comercial
> "Cuántos perros atendió cada comercial este mes?"

Claude usará `get_pets_per_salesperson` con `date_from` del primer día del mes.

### Comandas de mascotas
> "Muéstrame las comandas pendientes de hoy con sus peluqueros"

Claude usará `get_pet_comanda_details` con `service_state="pendiente"` y `date_from` de hoy.

### Vista general del negocio
> "Dame un resumen completo del estado del negocio hoy"

Claude usará el prompt `blackdog_daily_overview` que ejecuta 10 consultas para un panorama completo.

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
        ├── pdf_parser.py       # Extracción de datos de PDFs
        └── server.py           # Servidor MCP con todas las herramientas
```

## Licencia

MIT
