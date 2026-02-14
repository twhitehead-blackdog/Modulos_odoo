# Guia Completa - Odoo 18 MCP Server para Claude

> **Repositorio GitHub:** [https://github.com/twhitehead-blackdog/Modulos_odoo](https://github.com/twhitehead-blackdog/Modulos_odoo)
> **Rama:** `claude/odoo18-mcp-server-DF2M2`

---

## Que es este proyecto?

Un servidor **MCP (Model Context Protocol)** que permite a **Claude** (Desktop, Code, o cualquier cliente MCP) conectarse a una instancia de **Odoo 18** via XML-RPC y ejecutar operaciones de negocio directamente.

Con **88 herramientas**, **10 prompts predefinidos** y **1 recurso**, Claude puede:
- Consultar ventas, inventario, contabilidad, CRM, RRHH, manufactura y POS
- Crear/editar/eliminar registros en cualquier modelo
- Procesar PDFs de facturas y ordenes de compra
- Gestionar la operacion completa de **Black Dog Panama** (petshop + clinica veterinaria)
- Trackear comisiones de peluqueros y veterinarios
- Monitorear el workflow de comandas de mascotas en tiempo real

---

## Arquitectura

```
Claude (Desktop/Code/API)
    |
    | stdio (JSON-RPC 2.0)
    |
[odoo18-mcp-server]  ← FastMCP (Python)
    |
    | XML-RPC
    |
[Odoo 18 Instance]
    ├── /xmlrpc/2/common  (autenticacion)
    └── /xmlrpc/2/object  (execute_kw)
```

### Estructura del proyecto

```
Modulos_odoo/
├── pyproject.toml              # Config del proyecto (deps, entrypoint)
├── .env.example                # Plantilla de variables de entorno
├── .gitignore
├── README.md                   # Documentacion rapida
├── GUIA_COMPLETA.md            # ← Este archivo
└── src/
    └── odoo_mcp/
        ├── __init__.py
        ├── config.py           # OdooConfig dataclass + load_config()
        ├── odoo_client.py      # OdooClient (XML-RPC wrapper)
        ├── pdf_parser.py       # Extraccion de texto/tablas de PDFs
        └── server.py           # Servidor MCP (88 tools, 10 prompts, 1 resource)
```

### Dependencias

| Paquete | Version | Uso |
|---|---|---|
| `mcp[cli]` | >=1.2.0, <2 | SDK de Model Context Protocol (FastMCP) |
| `python-dotenv` | >=1.0.0 | Carga de variables de entorno desde .env |
| `pdfplumber` | >=0.10.0 | Extraccion de texto y tablas de PDFs |

---

## Instalacion

### Requisitos previos

- **Python 3.10+**
- **Instancia de Odoo 18** con XML-RPC habilitado (habilitado por defecto)
- **Git** para clonar el repositorio

### Pasos

```bash
# 1. Clonar el repositorio
git clone https://github.com/twhitehead-blackdog/Modulos_odoo.git
cd Modulos_odoo

# 2. Cambiar a la rama con todas las herramientas
git checkout claude/odoo18-mcp-server-DF2M2

# 3. Crear entorno virtual e instalar
python -m venv .venv

# Linux/Mac:
source .venv/bin/activate

# Windows PowerShell:
.\.venv\Scripts\Activate.ps1

# 4. Instalar en modo editable
pip install -e .

# 5. Verificar la instalacion
odoo18-mcp-server --help
```

### Windows (especifico)

```powershell
cd C:\Users\TuUsuario\Documents
git clone https://github.com/twhitehead-blackdog/Modulos_odoo.git odoo_mcp
cd odoo_mcp
git checkout claude/odoo18-mcp-server-DF2M2
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -e .

# Probar que funciona
.\.venv\Scripts\odoo18-mcp-server.exe
```

---

## Configuracion

### Variables de entorno

Crea un archivo `.env` en la raiz del proyecto:

```env
# Opcion 1: Usuario y contraseña
ODOO_URL=https://tu-instancia.odoo.com
ODOO_DB=tu-base-de-datos
ODOO_USERNAME=admin
ODOO_PASSWORD=tu-contraseña

# Opcion 2: API Key (alternativa, mas seguro)
ODOO_URL=https://tu-instancia.odoo.com
ODOO_DB=tu-base-de-datos
ODOO_API_KEY=tu-api-key-de-odoo
```

> **Nota:** Si usas API Key, no necesitas ODOO_USERNAME ni ODOO_PASSWORD.

### Configurar Claude Desktop

Edita `claude_desktop_config.json`:

**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
**Mac:** `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "odoo18": {
      "command": "C:\\Users\\trist\\Documents\\odoo_mcp\\.venv\\Scripts\\odoo18-mcp-server.exe",
      "env": {
        "ODOO_URL": "https://tu-instancia.odoo.com",
        "ODOO_DB": "tu-base-de-datos",
        "ODOO_USERNAME": "admin",
        "ODOO_PASSWORD": "tu-contraseña"
      }
    }
  }
}
```

**Con uv (alternativa):**

```json
{
  "mcpServers": {
    "odoo18": {
      "command": "uv",
      "args": [
        "--directory",
        "C:\\Users\\trist\\Documents\\odoo_mcp",
        "run",
        "odoo18-mcp-server"
      ],
      "env": {
        "ODOO_URL": "https://tu-instancia.odoo.com",
        "ODOO_DB": "tu-base-de-datos",
        "ODOO_USERNAME": "admin",
        "ODOO_PASSWORD": "tu-contraseña"
      }
    }
  }
}
```

### Configurar Claude Code

```bash
claude mcp add odoo18 -- \
  C:\Users\trist\Documents\odoo_mcp\.venv\Scripts\odoo18-mcp-server.exe

# O con variables de entorno explícitas:
claude mcp add odoo18 \
  -e ODOO_URL=https://tu-instancia.odoo.com \
  -e ODOO_DB=tu-base-de-datos \
  -e ODOO_USERNAME=admin \
  -e ODOO_PASSWORD=tu-contraseña \
  -- C:\Users\trist\Documents\odoo_mcp\.venv\Scripts\odoo18-mcp-server.exe
```

---

## Catalogo Completo de Herramientas (88 Tools)

---

### 1. General / CRUD (15 herramientas)

Operaciones basicas que funcionan con **cualquier modelo** de Odoo.

| # | Herramienta | Parametros | Descripcion |
|---|---|---|---|
| 1 | `test_connection` | *(ninguno)* | Verifica conexion con Odoo y retorna version del servidor + UID |
| 2 | `list_models` | `filter_name` | Lista modelos disponibles (ej: filtrar por 'sale' para ver modelos de venta) |
| 3 | `get_model_fields` | `model`, `filter_name` | Obtiene definicion de campos: tipo, requerido, readonly, opciones de selection |
| 4 | `search_records` | `model`, `domain`, `fields`, `limit`, `offset`, `order` | Busca y lee registros con filtros de dominio Odoo en JSON |
| 5 | `read_record` | `model`, `record_id`, `fields` | Lee un registro especifico por su ID |
| 6 | `create_record` | `model`, `values` | Crea un nuevo registro (values en JSON) |
| 7 | `update_record` | `model`, `record_id`, `values` | Actualiza un registro existente |
| 8 | `delete_record` | `model`, `record_id` | Elimina un registro |
| 9 | `count_records` | `model`, `domain` | Cuenta registros que cumplen un filtro |
| 10 | `search_by_name` | `model`, `name`, `limit` | Busca registros por nombre (display name) |
| 11 | `execute_method` | `model`, `method`, `record_ids`, `args`, `kwargs` | Ejecuta cualquier metodo del modelo (ej: action_confirm en sale.order) |
| 12 | `bulk_create_records` | `model`, `records_json` | Crea multiples registros de una vez |
| 13 | `bulk_update_records` | `model`, `record_ids`, `values` | Actualiza multiples registros de una vez |
| 14 | `get_default_values` | `model`, `fields` | Obtiene valores por defecto al crear un registro |
| 15 | `read_group_data` | `model`, `domain`, `fields`, `groupby`, `limit` | Datos agrupados/agregados (equivalente a GROUP BY en SQL) |

**Formato de dominios Odoo:**

```json
// Sin filtro
"[]"

// Filtro simple
"[[\"is_company\",\"=\",true]]"

// AND implicito
"[[\"name\",\"ilike\",\"juan\"],[\"active\",\"=\",true]]"

// OR explicito
"[\"|\",\"[\"state\",\"=\",\"draft\"]\",\"[\"state\",\"=\",\"sent\"]\"]"
```

---

### 2. CRM (2 herramientas)

| # | Herramienta | Parametros | Descripcion |
|---|---|---|---|
| 16 | `get_leads` | `stage`, `salesperson`, `partner_name`, `lead_type`, `limit` | Leads y oportunidades del CRM |
| 17 | `get_crm_pipeline_summary` | *(ninguno)* | Resumen del pipeline: cantidad y revenue esperado por etapa |

---

### 3. Ventas (6 herramientas)

| # | Herramienta | Parametros | Descripcion |
|---|---|---|---|
| 18 | `search_partner` | `name`, `email`, `is_company`, `limit` | Busca contactos/partners (atajo) |
| 19 | `get_sales_orders` | `state`, `partner_name`, `limit` | Ordenes de venta. Estados: draft, sent, sale, done, cancel |
| 20 | `get_sale_order_lines` | `order_name`, `product_name`, `limit` | Lineas detalladas de ordenes de venta |
| 21 | `get_products` | `name`, `product_type`, `limit` | Productos. Tipos: consu, service, product |
| 22 | `get_sales_summary` | `date_from`, `date_to`, `group_by` | Resumen agrupado por partner_id, user_id o state |
| 23 | `get_pos_orders` | `session_name`, `partner_name`, `state`, `date_from`, `limit` | Ordenes de Punto de Venta |

---

### 4. Compras (1 herramienta)

| # | Herramienta | Parametros | Descripcion |
|---|---|---|---|
| 24 | `get_purchase_orders` | `state`, `partner_name`, `limit` | Ordenes de compra. Estados: draft, sent, purchase, done, cancel |

---

### 5. Inventario / Almacen (4 herramientas)

| # | Herramienta | Parametros | Descripcion |
|---|---|---|---|
| 25 | `get_stock_pickings` | `picking_type`, `state`, `partner_name`, `limit` | Transferencias: incoming (recepciones), outgoing (envios), internal |
| 26 | `get_stock_quants` | `product_name`, `location_name`, `limit` | Niveles de stock actuales por ubicacion |
| 27 | `get_stock_moves` | `product_name`, `state`, `limit` | Movimientos individuales de stock entre ubicaciones |
| 28 | `get_warehouses` | *(ninguno)* | Lista todos los almacenes configurados |

---

### 6. Contabilidad / Finanzas (7 herramientas)

| # | Herramienta | Parametros | Descripcion |
|---|---|---|---|
| 29 | `get_invoices` | `state`, `partner_name`, `move_type`, `limit` | Facturas. Tipos: out_invoice, in_invoice, out_refund, in_refund |
| 30 | `get_invoice_lines` | `invoice_name`, `account_code`, `limit` | Lineas detalladas de facturas |
| 31 | `get_payments` | `payment_type`, `partner_name`, `state`, `limit` | Pagos. Tipos: inbound (cobros), outbound (pagos a proveedores) |
| 32 | `get_journal_entries` | `journal_name`, `state`, `date_from`, `date_to`, `limit` | Asientos contables (no facturas) |
| 33 | `get_journal_items` | `account_code`, `partner_name`, `date_from`, `date_to`, `limit` | Apuntes contables individuales (debito/credito) |
| 34 | `get_account_balances` | `account_type`, `code_prefix` | Saldos por cuenta (balance de comprobacion) |
| 35 | `get_contacts_with_overdue_invoices` | *(ninguno)* | Contactos con facturas vencidas y monto pendiente |

---

### 7. Recursos Humanos (3 herramientas)

| # | Herramienta | Parametros | Descripcion |
|---|---|---|---|
| 36 | `get_employees` | `name`, `department`, `job_title`, `limit` | Empleados con filtros |
| 37 | `get_departments` | *(ninguno)* | Todos los departamentos con manager y conteo |
| 38 | `get_leaves` | `employee_name`, `state`, `date_from`, `limit` | Solicitudes de ausencia/vacaciones |

---

### 8. Proyectos (2 herramientas)

| # | Herramienta | Parametros | Descripcion |
|---|---|---|---|
| 39 | `get_projects` | `name`, `manager`, `limit` | Proyectos |
| 40 | `get_tasks` | `project_name`, `assignee`, `stage`, `priority`, `limit` | Tareas de proyectos |

---

### 9. Manufactura (2 herramientas)

| # | Herramienta | Parametros | Descripcion |
|---|---|---|---|
| 41 | `get_manufacturing_orders` | `product_name`, `state`, `limit` | Ordenes de produccion (MRP) |
| 42 | `get_bill_of_materials` | `product_name`, `limit` | Listas de materiales (BoM) |

---

### 10. Utilidades del Sistema (5 herramientas)

| # | Herramienta | Parametros | Descripcion |
|---|---|---|---|
| 43 | `get_company_info` | *(ninguno)* | Informacion de la empresa actual |
| 44 | `get_users` | `active_only`, `limit` | Usuarios del sistema |
| 45 | `get_chatter_messages` | `model`, `record_id`, `limit` | Mensajes del chatter de cualquier registro |
| 46 | `get_activities` | `model`, `user_name`, `overdue_only`, `limit` | Actividades programadas (pendientes, vencidas) |
| 47 | `get_installed_modules` | `filter_name`, `state` | Modulos instalados/disponibles |

---

### 11. PDF / Documentos (6 herramientas)

| # | Herramienta | Parametros | Descripcion |
|---|---|---|---|
| 48 | `parse_pdf` | `file_path` | Extrae texto, tablas y montos de un PDF |
| 49 | `parse_pdf_and_create_vendor_bill` | `file_path` | Analiza PDF de factura y prepara datos estructurados |
| 50 | `create_vendor_bill` | `partner_name`, `invoice_date`, `ref`, `lines_json`, `currency` | Crea factura de proveedor con lineas |
| 51 | `create_purchase_order_with_lines` | `partner_name`, `lines_json`, `date_order`, `notes`, `currency` | Crea OC con lineas |
| 52 | `create_sale_order_with_lines` | `partner_name`, `lines_json`, `date_order`, `notes` | Crea orden de venta con lineas |
| 53 | `attach_file_to_record` | `file_path`, `model`, `record_id`, `description` | Adjunta archivo (PDF, imagen) a un registro |

**Flujo tipico para procesar un PDF:**
1. `parse_pdf` o `parse_pdf_and_create_vendor_bill` - extraer datos
2. Claude analiza y estructura los datos
3. `create_vendor_bill` o `create_purchase_order_with_lines` - crear el registro
4. `attach_file_to_record` - adjuntar el PDF original

---

### 12. Petshop y Clinica Veterinaria (5 herramientas)

Modulo: `petshop_clinica` | Modelos: `x_pet`, `mascota.raza`, `pet.service.template`, `pet.service.history`, `pet.vaccine.history`

| # | Herramienta | Parametros | Descripcion |
|---|---|---|---|
| 54 | `get_pets` | `owner_name`, `species`, `name`, `vaccinated`, `limit` | Busca mascotas (perro, gato, otro) |
| 55 | `get_pet_details` | `pet_id` | Detalle completo de mascota + historial de servicios y vacunas |
| 56 | `get_pet_breeds` | `species` | Catalogo de razas |
| 57 | `get_pet_service_templates` | `service_type` | Plantillas de servicios (bath, cut, spa) |
| 58 | `get_pets_with_overdue_vaccines` | *(ninguno)* | Mascotas que necesitan vacunacion |

---

### 13. Auditoria Operativa (2 herramientas)

Modulo: `audit_control` | Modelo: `audit.log`

| # | Herramienta | Parametros | Descripcion |
|---|---|---|---|
| 59 | `get_audit_logs` | `audit_type`, `severity`, `state`, `date_from`, `date_to`, `user_name`, `limit` | Logs de auditoria (sales, inventory, finance, security) |
| 60 | `get_audit_summary` | *(ninguno)* | Resumen de auditorias abiertas por tipo y severidad |

---

### 14. Control de Vencimientos (2 herramientas)

Modulo: `inventory_expiry_control` | Modelo: `inventory.expiry.line`

| # | Herramienta | Parametros | Descripcion |
|---|---|---|---|
| 61 | `get_expiring_products` | `state`, `warehouse_name`, `product_name`, `handled`, `limit` | Productos por vencer. Estados: expired, one_month, three_months, six_months |
| 62 | `get_expiry_summary` | *(ninguno)* | Resumen por estado y almacen con valor en riesgo |

---

### 15. Ajustes de Inventario (1 herramienta)

Modulo: `inventory_adjustment_custom_report` | Modelo: `inventory.adjustment.log`

| # | Herramienta | Parametros | Descripcion |
|---|---|---|---|
| 63 | `get_inventory_adjustment_logs` | `product_name`, `warehouse_name`, `impact_level`, `reviewed`, `date_from`, `date_to`, `limit` | Logs de ajustes con impacto: low, medium, high, critical |

---

### 16. Transferencias entre Tiendas (1 herramienta)

Modulo: `store_transfer_request` | Modelo: `store.transfer.request`

| # | Herramienta | Parametros | Descripcion |
|---|---|---|---|
| 64 | `get_transfer_requests` | `state`, `warehouse_dest`, `reason`, `limit` | Solicitudes de transferencia (draft → submitted → approved → done) |

---

### 17. Reabastecimiento Estimado (1 herramienta)

Modulo: `estimated_replenishment` | Modelos: `estimated.replenishment.order`, `estimated.replenishment.wh.order`

| # | Herramienta | Parametros | Descripcion |
|---|---|---|---|
| 65 | `get_replenishment_orders` | `state`, `order_type`, `limit` | Ordenes de reabastecimiento (store o warehouse) |

---

### 18. Metas de Ventas y Analitica (2 herramientas)

Modulo: `meta_ventas_analiticas` | Modelos: `meta.mensual`, `meta.analitica.historica`

| # | Herramienta | Parametros | Descripcion |
|---|---|---|---|
| 66 | `get_sales_targets` | `month`, `year`, `account_name`, `limit` | Metas mensuales (baja, promedio, alta, oro) por cuenta analitica |
| 67 | `get_sales_target_performance` | `month`, `year`, `account_name`, `limit` | Rendimiento real vs metas con %, crecimiento y nivel |

---

### 19. Segmentacion de Clientes (2 herramientas)

Modulo: `res_partner_segmentation` | 60+ campos computados en `res.partner`

| # | Herramienta | Parametros | Descripcion |
|---|---|---|---|
| 68 | `get_customer_segmentation` | `segment`, `rfm_tier`, `churn_risk`, `value_segment`, `limit` | Datos RFM, valor, riesgo por cliente |
| 69 | `get_customer_segmentation_summary` | *(ninguno)* | Resumen por tier (diamante/oro/plata/bronce), valor y riesgo de abandono |

**Opciones de filtro:**
- `rfm_tier`: diamante, oro, plata, bronce, nuevo
- `churn_risk`: alto, medio, bajo, ninguno
- `value_segment`: vip, premium, regular, bajo
- `segment`: menos_30, menos_60, menos_90, mas_90

---

### 20. Aprobacion de Productos (1 herramienta)

Modulo: `product_approval_flow` | Modelo: `product.request`

| # | Herramienta | Parametros | Descripcion |
|---|---|---|---|
| 70 | `get_product_requests` | `state`, `requester`, `category`, `limit` | Solicitudes de productos (draft → to_approve → approved/rejected) |

---

### 21. Aprobacion de Compras (1 herramienta)

Modulo: `purchase_approval_flow` | Campos en `purchase.order`

| # | Herramienta | Parametros | Descripcion |
|---|---|---|---|
| 71 | `get_purchase_approval_status` | `approval_state`, `partner_name`, `has_risk`, `limit` | Nivel 1 (3+ meses inventario), Nivel 2 (6+ meses) |

---

### 22. Pasarelas de Pago (2 herramientas)

Modulos: `tilopay_payment`, `yappy_payment`

| # | Herramienta | Parametros | Descripcion |
|---|---|---|---|
| 72 | `get_tilopay_transactions` | `state`, `partner_name`, `limit` | Transacciones de pago Tilopay (Panama) |
| 73 | `get_yappy_transactions` | `state`, `limit` | Transacciones de pago Yappy (movil Panama) |

---

### 23. Mensajeria WhatsApp (3 herramientas)

Modulos: `respond_buttons`, `wassenger_integration`

| # | Herramienta | Parametros | Descripcion |
|---|---|---|---|
| 74 | `get_respond_message_logs` | `status`, `phone`, `limit` | Logs de mensajes Respond.io |
| 75 | `get_respond_buttons` | *(ninguno)* | Plantillas/botones de WhatsApp configurados |
| 76 | `get_wassenger_message_logs` | `status`, `phone`, `limit` | Logs de mensajes Wassenger |

---

### 24. Shopify (2 herramientas)

Modulo: `shopify_ept`

| # | Herramienta | Parametros | Descripcion |
|---|---|---|---|
| 77 | `get_shopify_instances` | *(ninguno)* | Instancias Shopify configuradas |
| 78 | `get_shopify_products` | `name`, `exported`, `limit` | Productos sincronizados con Shopify |

---

### 25. Margenes de Producto (1 herramienta)

Modulo: `product_margen_sugerido`

| # | Herramienta | Parametros | Descripcion |
|---|---|---|---|
| 79 | `get_product_margins` | `product_name`, `category`, `profitability`, `limit` | Markup %, margen bruto, precio sugerido, nivel rentabilidad |

---

### 26. Discrepancias de Inventario (1 herramienta)

Modulo: `stock_inventory_discrepancy`

| # | Herramienta | Parametros | Descripcion |
|---|---|---|---|
| 80 | `get_stock_discrepancies` | `product_name`, `over_threshold`, `limit` | Diferencia entre inventario teorico y fisico |

---

### 27. Comisiones de Peluqueros y Veterinarios (4 herramientas)

Modulo: `sale_order_comanda_mascotas` | Modelos SQL View: `comision.estilista`, `comision.estilista.resumen`, `comision.veterinario.resumen`, `sancion.peluquero`

| # | Herramienta | Parametros | Descripcion |
|---|---|---|---|
| 81 | `get_groomer_commissions` | `groomer_name`, `month`, `year`, `branch_name`, `limit` | Lineas detalladas: servicio, monto, % compartido entre estilistas |
| 82 | `get_groomer_commission_summary` | `groomer_name`, `month`, `year`, `limit` | Resumen mensual: total servicios, ventas, comision, sanciones, monto final, ranking |
| 83 | `get_vet_commission_summary` | `vet_name`, `month`, `year`, `limit` | Resumen mensual de comisiones veterinarias |
| 84 | `get_groomer_sanctions` | `groomer_name`, `sanction_type`, `state`, `date_from`, `date_to`, `limit` | Sanciones: ausencia, tardanza, queja, otro |

**Como funcionan las comisiones:**
- Se calculan desde **POS orders** (ventas de caja) para productos de la categoria **Peluqueria**
- Si 2 peluqueros comparten un servicio, el monto se divide equitativamente
- Las sanciones (ausencias, tardanzas, quejas) reducen la comision final con un %
- `comision.estilista` y `comision.estilista.resumen` son **SQL Views** (no tablas regulares)

---

### 28. Mascotas por Comercial (3 herramientas)

Modelo: `x.mascota.line` + campos computados en `sale.order`

| # | Herramienta | Parametros | Descripcion |
|---|---|---|---|
| 85 | `get_pets_per_salesperson` | `salesperson_name`, `date_from`, `date_to`, `service_type`, `limit` | Cantidad de mascotas atendidas por vendedor |
| 86 | `get_pet_service_lines_by_commercial` | `date_from`, `date_to` | Resumen agrupado: ordenes, mascotas y monto por comercial |
| 87 | `get_pet_comanda_details` | `order_name`, `pet_name`, `groomer_name`, `service_state`, `date_from`, `limit` | Comandas detalladas con peluqueros asignados, servicios y estado |

**Estados del servicio:** `pendiente` → `confirmado` → `en_proceso` → `terminado` → `entregado` | `no_se_presento` | `cancelado`

---

### 29. Workflow de Comandas (6 herramientas)

Modulo: `sale_order_comanda_mascotas` | Modelos: `x.mascota.line`, `x.mascota.atencion.historial`, `x.mascota.checklist`

| # | Herramienta | Parametros | Descripcion |
|---|---|---|---|
| 88 | `get_comanda_workflow_status` | `date_from`, `date_to`, `branch_name` | Pipeline de estados por tipo de servicio y prioridad |
| 89 | `get_groomer_time_tracking` | `groomer_name`, `date_from`, `date_to`, `service_type`, `state`, `limit` | Registros de atencion con duracion, calificacion, servicio |
| 90 | `get_groomer_productivity` | `date_from`, `date_to` | Productividad por staff: horas, servicios, promedio |
| 91 | `get_comanda_checklist_status` | `order_name`, `pet_name`, `checklist_type`, `pending_only`, `limit` | Checklists obligatorios/opcionales por mascota |
| 92 | `get_comanda_services_ranking` | `date_from`, `date_to` | Ranking de servicios mas solicitados con % |
| 93 | `get_comanda_orders_summary` | `date_from`, `date_to`, `salesperson_name`, `service_type`, `limit` | Ordenes con contadores de mascotas por tipo |

> **Nota:** El total real es 88 herramientas unicas. Los numeros 89-93 son continuacion de la numeracion del catalogo.

**Servicios de peluqueria rastreados:** bano, corte, acicalado, mantenimiento, rapado, deslanado, profilaxis dental, tinte, corte de unas, limpieza de oidos, peluqueria express

**Servicios veterinarios rastreados:** vacunacion, desparasitacion, consulta general, consulta dermatologica, cirugia menor, analisis de sangre, analisis quimica

---

## Prompts Predefinidos (10)

Los prompts generan instrucciones paso a paso para que Claude ejecute multiples herramientas en secuencia.

| # | Prompt | Parametros | Que hace |
|---|---|---|---|
| 1 | `explore_model` | `model` | Explora estructura y datos de cualquier modelo Odoo |
| 2 | `analyze_sales` | *(ninguno)* | Analisis de ventas por estado y por cliente |
| 3 | `analyze_inventory` | `product` | Analisis de inventario, almacenes y transferencias |
| 4 | `analyze_receivables` | *(ninguno)* | Analisis de cuentas por cobrar |
| 5 | `daily_overview` | *(ninguno)* | Vista general diaria (actividades, cotizaciones, entregas, cobranza) |
| 6 | `process_pdf_invoice` | `file_path` | Procesa PDF → crea factura de proveedor → adjunta PDF |
| 7 | `process_pdf_purchase_order` | `file_path` | Procesa PDF → crea orden de compra → adjunta PDF |
| 8 | `blackdog_daily_overview` | *(ninguno)* | **Vista completa Black Dog:** auditorias, vencimientos, transferencias, aprobaciones, metas, churn, vacunas, entregas, cobranza |
| 9 | `analyze_pet_owner` | `owner_name` | Perfil completo de un dueno: mascotas, servicios, vacunas, gasto, segmentacion |
| 10 | *(no numerado)* | | |

---

## Recurso MCP

| URI | Descripcion |
|---|---|
| `odoo://info` | URL, base de datos, version y UID de la instancia conectada |

---

## Ejemplos de Uso (desde Claude)

### Operaciones basicas

**Verificar conexion:**
> "Conectate a Odoo y dime que version tienes"

**Explorar un modelo:**
> "Muestrame los campos del modelo sale.order"

**Buscar registros:**
> "Busca todos los contactos que sean empresas"

**Crear un contacto:**
> "Crea un nuevo contacto llamado Juan Perez con email juan@example.com"

### Ventas y CRM

**Pipeline CRM:**
> "Dame un resumen del pipeline de ventas"

**Ventas por vendedor:**
> "Cuanto vendio cada vendedor el mes pasado?"

**Ordenes pendientes:**
> "Muestrame las ordenes de venta en estado borrador"

### Inventario

**Stock de un producto:**
> "Cuantas unidades hay del producto 'Laptop Pro' en todos los almacenes?"

**Transferencias pendientes:**
> "Que transferencias estan listas para enviar?"

### Contabilidad

**Facturas vencidas:**
> "Que clientes tienen facturas vencidas?"

**Balance de cuentas:**
> "Muestrame el balance de las cuentas de ingreso"

### PDF

**Procesar factura:**
> "Tengo esta factura en PDF: /tmp/factura.pdf - creala como factura de proveedor en Odoo"

### Black Dog - Mascotas

**Mascotas de un cliente:**
> "Muestrame las mascotas de Juan Perez con su historial de vacunas"

**Vacunas pendientes:**
> "Que mascotas necesitan vacunacion?"

### Black Dog - Operaciones

**Alertas criticas:**
> "Hay alertas criticas de auditoria abiertas?"

**Productos por vencer:**
> "Que productos estan por vencer en los proximos 30 dias?"

**Metas de ventas:**
> "Como vamos con las metas de ventas de enero 2025?"

**Clientes en riesgo:**
> "Que clientes VIP estan en riesgo de irse?"

### Black Dog - Comisiones

**Comisiones mensuales:**
> "Cuanto gano cada peluquero en enero 2025?"

**Detalle de un peluquero:**
> "Muestrame los servicios y comisiones de Maria en febrero"

**Sanciones:**
> "Que sanciones tiene Pedro este mes?"

### Black Dog - Comandas

**Pipeline de hoy:**
> "Como esta el flujo de comandas de hoy? Cuantas pendientes, en proceso y terminadas?"

**Productividad:**
> "Quien fue el peluquero mas productivo esta semana?"

**Servicios populares:**
> "Cuales son los servicios mas populares del mes?"

**Checklists pendientes:**
> "Que checklists de mascotas estan pendientes de completar?"

**Vista general diaria:**
> "Dame un resumen completo del estado del negocio hoy"

---

## Cliente XML-RPC (OdooClient)

La clase `OdooClient` en `odoo_client.py` envuelve toda la comunicacion XML-RPC con Odoo:

| Metodo | Descripcion |
|---|---|
| `authenticate()` | Autentica y retorna el UID |
| `server_version()` | Version del servidor |
| `execute_kw(model, method, args, kwargs)` | Ejecuta cualquier metodo RPC |
| `search(model, domain, offset, limit, order)` | Busca IDs |
| `search_read(model, domain, fields, offset, limit, order)` | Busca y lee en una sola llamada |
| `read(model, ids, fields)` | Lee registros por IDs |
| `create(model, values)` | Crea un registro |
| `write(model, ids, values)` | Actualiza registros |
| `unlink(model, ids)` | Elimina registros |
| `search_count(model, domain)` | Cuenta registros |
| `fields_get(model, attributes)` | Definiciones de campos |
| `name_search(model, name, domain, limit)` | Busca por display name |
| `read_group(model, domain, fields, groupby, limit, orderby, lazy)` | GROUP BY |
| `create_multi(model, values_list)` | Crea multiples registros |
| `default_get(model, fields)` | Valores por defecto |

---

## Modulos Black Dog Integrados

Estos son los **48 modulos personalizados** del repositorio `blackdogpanama` que fueron analizados para crear las herramientas:

| Modulo | Modelo principal | Herramientas |
|---|---|---|
| `petshop_clinica` | x_pet, mascota.raza, pet.service.template | 5 |
| `audit_control` | audit.log | 2 |
| `inventory_expiry_control` | inventory.expiry.line | 2 |
| `inventory_adjustment_custom_report` | inventory.adjustment.log | 1 |
| `store_transfer_request` | store.transfer.request | 1 |
| `estimated_replenishment` | estimated.replenishment.order | 1 |
| `meta_ventas_analiticas` | meta.mensual, meta.analitica.historica | 2 |
| `res_partner_segmentation` | res.partner (60+ campos) | 2 |
| `product_approval_flow` | product.request | 1 |
| `purchase_approval_flow` | purchase.order (campos extra) | 1 |
| `tilopay_payment` | tilopay.payment.transaction | 1 |
| `yappy_payment` | yappy.payment.transaction | 1 |
| `respond_buttons` | respond.button, respond.message.log | 2 |
| `wassenger_integration` | wassenger.message.log | 1 |
| `shopify_ept` | shopify.instance.ept, shopify.product.product.ept | 2 |
| `product_margen_sugerido` | product.template (campos extra) | 1 |
| `stock_inventory_discrepancy` | stock.quant (campos extra) | 1 |
| `sale_order_comanda_mascotas` | x.mascota.line, comision.estilista, x.mascota.atencion.historial, x.mascota.checklist | 13 |

---

## Troubleshooting

### Error: `FastMCP.__init__() got an unexpected keyword argument 'description'`

Versiones de `mcp >= 1.12.3` ya no aceptan `description`. Ya esta corregido en la rama actual.

### Error de conexion XML-RPC

Verifica que:
1. La URL de Odoo es correcta y accesible
2. El nombre de la base de datos es exacto
3. Las credenciales son correctas
4. El firewall permite la conexion

### Modulos personalizados no encontrados

Si una herramienta de Black Dog falla con "model not found", el modulo correspondiente no esta instalado en tu instancia de Odoo. Instala el modulo desde el repositorio `blackdogpanama`.

### Windows: el servidor no arranca

```powershell
# Asegurate de estar en el directorio correcto
cd C:\Users\trist\Documents\odoo_mcp

# Activa el venv
.\.venv\Scripts\Activate.ps1

# Reinstala
py -m pip install -e .

# Ejecuta
.\.venv\Scripts\odoo18-mcp-server.exe
```

---

## Desarrollo y Testing

```bash
# Instalar en modo desarrollo
pip install -e ".[dev]"

# Probar con el inspector MCP (abre interfaz web)
uv run mcp dev src/odoo_mcp/server.py

# Ejecutar directamente (stdio)
uv run odoo18-mcp-server

# Ver logs (van a stderr, no interfieren con JSON-RPC en stdout)
uv run odoo18-mcp-server 2> /tmp/mcp_odoo.log
```

---

## Licencia

MIT

---

> **Repositorio:** [https://github.com/twhitehead-blackdog/Modulos_odoo](https://github.com/twhitehead-blackdog/Modulos_odoo)
> **Rama:** `claude/odoo18-mcp-server-DF2M2`
> **Total herramientas:** 88 | **Prompts:** 10 | **Recursos:** 1
