"""MCP Server for Odoo 18 - Exposes Odoo operations as tools for Claude."""

import json
import logging
import sys
from typing import Any

from mcp.server.fastmcp import FastMCP

from .config import load_config
from .odoo_client import OdooClient

# Configure logging to stderr (stdout is reserved for JSON-RPC in stdio transport)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("odoo_mcp")

# Initialize MCP server
mcp = FastMCP(
    "odoo18",
    description="MCP server for interacting with Odoo 18 via XML-RPC",
)

# Lazy-initialized client
_client: OdooClient | None = None


def get_client() -> OdooClient:
    """Get or create the Odoo client singleton."""
    global _client
    if _client is None:
        config = load_config()
        _client = OdooClient(config)
    return _client


def _format_records(records: list[dict[str, Any]], max_records: int = 50) -> str:
    """Format records for display, truncating if necessary."""
    if not records:
        return "No records found."
    truncated = len(records) > max_records
    records = records[:max_records]
    result = json.dumps(records, indent=2, default=str, ensure_ascii=False)
    if truncated:
        result += f"\n\n... (showing first {max_records} records, use limit/offset for pagination)"
    return result


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@mcp.tool()
def test_connection() -> str:
    """Test the connection to Odoo and return server info.

    Use this tool first to verify that the Odoo instance is reachable
    and credentials are valid.
    """
    client = get_client()
    version = client.server_version()
    uid = client.uid
    return f"Connected to Odoo {version} (uid={uid}) at {client.config.base_url}"


@mcp.tool()
def list_models(filter_name: str = "") -> str:
    """List available Odoo models.

    Args:
        filter_name: Optional filter string to search models by name
                     (e.g. 'sale' to find sale-related models).
    """
    client = get_client()
    domain: list[Any] = []
    if filter_name:
        domain = [("model", "ilike", filter_name)]
    models = client.search_read(
        "ir.model",
        domain=domain,
        fields=["model", "name"],
        limit=100,
        order="model",
    )
    if not models:
        return "No models found matching the filter."
    lines = [f"- {m['model']}  ({m['name']})" for m in models]
    return f"Found {len(models)} models:\n" + "\n".join(lines)


@mcp.tool()
def get_model_fields(model: str, filter_name: str = "") -> str:
    """Get field definitions for an Odoo model.

    Args:
        model: The technical model name (e.g. 'res.partner', 'sale.order').
        filter_name: Optional filter to show only fields whose name contains this string.
    """
    client = get_client()
    fields = client.fields_get(model)
    if filter_name:
        fields = {k: v for k, v in fields.items() if filter_name.lower() in k.lower()}
    if not fields:
        return f"No fields found for model '{model}' with filter '{filter_name}'."

    lines = []
    for name, info in sorted(fields.items()):
        ftype = info.get("type", "?")
        label = info.get("string", "")
        required = " [REQUIRED]" if info.get("required") else ""
        readonly = " [readonly]" if info.get("readonly") else ""
        selection = ""
        if ftype == "selection" and info.get("selection"):
            opts = ", ".join(f"{k}={v}" for k, v in info["selection"])
            selection = f" options=[{opts}]"
        lines.append(f"- {name} ({ftype}): {label}{required}{readonly}{selection}")

    return f"Fields for '{model}' ({len(lines)} fields):\n" + "\n".join(lines)


@mcp.tool()
def search_records(
    model: str,
    domain: str = "[]",
    fields: str = "",
    limit: int = 20,
    offset: int = 0,
    order: str = "",
) -> str:
    """Search and read records from an Odoo model.

    Args:
        model: The technical model name (e.g. 'res.partner', 'sale.order').
        domain: Odoo domain filter as JSON string. Examples:
                '[]' - no filter (all records)
                '[["is_company","=",true]]' - only companies
                '[["name","ilike","john"],["active","=",true]]' - name contains john AND active
                '["|",["state","=","draft"],["state","=","sent"]]' - draft OR sent
        fields: Comma-separated list of field names to read (e.g. 'name,email,phone').
                Leave empty to read all fields.
        limit: Maximum number of records to return (default 20, max 100).
        offset: Number of records to skip for pagination.
        order: Sort order (e.g. 'name asc', 'create_date desc').
    """
    client = get_client()
    parsed_domain = json.loads(domain)
    field_list = [f.strip() for f in fields.split(",") if f.strip()] if fields else None
    limit = min(limit, 100)

    records = client.search_read(
        model,
        domain=parsed_domain,
        fields=field_list,
        limit=limit,
        offset=offset,
        order=order or None,
    )
    count = client.search_count(model, domain=parsed_domain)
    header = f"Model: {model} | Showing {len(records)} of {count} total records"
    if offset:
        header += f" (offset: {offset})"
    return header + "\n\n" + _format_records(records)


@mcp.tool()
def read_record(model: str, record_id: int, fields: str = "") -> str:
    """Read a single record by its ID.

    Args:
        model: The technical model name (e.g. 'res.partner').
        record_id: The ID of the record to read.
        fields: Comma-separated list of field names to read.
                Leave empty to read all fields.
    """
    client = get_client()
    field_list = [f.strip() for f in fields.split(",") if f.strip()] if fields else None
    records = client.read(model, [record_id], fields=field_list)
    if not records:
        return f"Record with ID {record_id} not found in model '{model}'."
    return json.dumps(records[0], indent=2, default=str, ensure_ascii=False)


@mcp.tool()
def create_record(model: str, values: str) -> str:
    """Create a new record in an Odoo model.

    Args:
        model: The technical model name (e.g. 'res.partner').
        values: JSON string with field values. Example:
                '{"name": "John Doe", "email": "john@example.com", "is_company": false}'
    """
    client = get_client()
    parsed_values = json.loads(values)
    record_id = client.create(model, parsed_values)
    return f"Record created successfully in '{model}' with ID: {record_id}"


@mcp.tool()
def update_record(model: str, record_id: int, values: str) -> str:
    """Update an existing record in Odoo.

    Args:
        model: The technical model name (e.g. 'res.partner').
        record_id: The ID of the record to update.
        values: JSON string with field values to update. Example:
                '{"email": "new@example.com", "phone": "+1234567890"}'
    """
    client = get_client()
    parsed_values = json.loads(values)
    client.write(model, [record_id], parsed_values)
    return f"Record {record_id} updated successfully in '{model}'."


@mcp.tool()
def delete_record(model: str, record_id: int) -> str:
    """Delete a record from Odoo.

    Args:
        model: The technical model name (e.g. 'res.partner').
        record_id: The ID of the record to delete.
    """
    client = get_client()
    client.unlink(model, [record_id])
    return f"Record {record_id} deleted successfully from '{model}'."


@mcp.tool()
def count_records(model: str, domain: str = "[]") -> str:
    """Count records matching a domain filter.

    Args:
        model: The technical model name (e.g. 'res.partner').
        domain: Odoo domain filter as JSON string (same format as search_records).
    """
    client = get_client()
    parsed_domain = json.loads(domain)
    count = client.search_count(model, domain=parsed_domain)
    return f"Model '{model}' has {count} records matching the domain."


@mcp.tool()
def search_by_name(model: str, name: str, limit: int = 10) -> str:
    """Search records by their display name.

    This is useful for quickly finding records when you know the name
    but not the ID (e.g. finding a partner named 'Acme Corp').

    Args:
        model: The technical model name (e.g. 'res.partner').
        name: The name to search for (partial matches supported).
        limit: Maximum number of results (default 10).
    """
    client = get_client()
    results = client.name_search(model, name=name, limit=limit)
    if not results:
        return f"No records found in '{model}' matching name '{name}'."
    lines = [f"- ID {r[0]}: {r[1]}" for r in results]
    return f"Found {len(results)} records in '{model}':\n" + "\n".join(lines)


@mcp.tool()
def execute_method(
    model: str,
    method: str,
    record_ids: str = "[]",
    args: str = "[]",
    kwargs: str = "{}",
) -> str:
    """Execute a custom method on an Odoo model.

    This is an advanced tool for calling any method exposed by an Odoo model
    (e.g. action_confirm on sale.order, button_validate on stock.picking).

    Args:
        model: The technical model name (e.g. 'sale.order').
        method: The method name to call (e.g. 'action_confirm').
        record_ids: JSON array of record IDs to call the method on (e.g. '[1, 2, 3]').
        args: JSON array of additional positional arguments.
        kwargs: JSON object with additional keyword arguments.
    """
    client = get_client()
    parsed_ids = json.loads(record_ids)
    parsed_args = json.loads(args)
    parsed_kwargs = json.loads(kwargs)

    call_args = [parsed_ids] + parsed_args if parsed_ids else parsed_args
    result = client.execute_kw(model, method, call_args, parsed_kwargs)
    return f"Method '{model}.{method}' executed.\nResult: {json.dumps(result, indent=2, default=str, ensure_ascii=False)}"


@mcp.tool()
def search_partner(
    name: str = "",
    email: str = "",
    is_company: bool | None = None,
    limit: int = 20,
) -> str:
    """Search for contacts/partners in Odoo with common filters.

    This is a convenience tool for the most common search: finding contacts.

    Args:
        name: Filter by name (partial match).
        email: Filter by email (partial match).
        is_company: Filter by type - True for companies, False for individuals, None for both.
        limit: Maximum number of results.
    """
    domain: list[Any] = []
    if name:
        domain.append(["name", "ilike", name])
    if email:
        domain.append(["email", "ilike", email])
    if is_company is not None:
        domain.append(["is_company", "=", is_company])

    client = get_client()
    records = client.search_read(
        "res.partner",
        domain=domain,
        fields=["name", "email", "phone", "is_company", "city", "country_id"],
        limit=limit,
        order="name",
    )
    count = client.search_count("res.partner", domain=domain)
    header = f"Partners: showing {len(records)} of {count} total"
    return header + "\n\n" + _format_records(records)


@mcp.tool()
def get_sales_orders(
    state: str = "",
    partner_name: str = "",
    limit: int = 20,
) -> str:
    """Get sales orders with common filters.

    Args:
        state: Filter by state (draft, sent, sale, done, cancel). Leave empty for all.
        partner_name: Filter by customer name (partial match).
        limit: Maximum number of results.
    """
    domain: list[Any] = []
    if state:
        domain.append(["state", "=", state])
    if partner_name:
        domain.append(["partner_id.name", "ilike", partner_name])

    client = get_client()
    records = client.search_read(
        "sale.order",
        domain=domain,
        fields=["name", "partner_id", "state", "date_order", "amount_total", "currency_id"],
        limit=limit,
        order="date_order desc",
    )
    count = client.search_count("sale.order", domain=domain)
    header = f"Sales Orders: showing {len(records)} of {count} total"
    return header + "\n\n" + _format_records(records)


@mcp.tool()
def get_invoices(
    state: str = "",
    partner_name: str = "",
    move_type: str = "out_invoice",
    limit: int = 20,
) -> str:
    """Get invoices/bills with common filters.

    Args:
        state: Filter by state (draft, posted, cancel). Leave empty for all.
        partner_name: Filter by partner name (partial match).
        move_type: Type of document: 'out_invoice' (customer invoice),
                   'in_invoice' (vendor bill), 'out_refund' (credit note),
                   'in_refund' (vendor credit note). Default: 'out_invoice'.
        limit: Maximum number of results.
    """
    domain: list[Any] = [["move_type", "=", move_type]]
    if state:
        domain.append(["state", "=", state])
    if partner_name:
        domain.append(["partner_id.name", "ilike", partner_name])

    client = get_client()
    records = client.search_read(
        "account.move",
        domain=domain,
        fields=[
            "name", "partner_id", "state", "move_type",
            "invoice_date", "amount_total", "amount_residual", "currency_id",
        ],
        limit=limit,
        order="invoice_date desc",
    )
    count = client.search_count("account.move", domain=domain)
    header = f"Invoices: showing {len(records)} of {count} total"
    return header + "\n\n" + _format_records(records)


@mcp.tool()
def get_products(
    name: str = "",
    product_type: str = "",
    limit: int = 20,
) -> str:
    """Get products with common filters.

    Args:
        name: Filter by product name (partial match).
        product_type: Filter by type ('consu' for consumable, 'service' for service,
                      'product' for storable). Leave empty for all.
        limit: Maximum number of results.
    """
    domain: list[Any] = []
    if name:
        domain.append(["name", "ilike", name])
    if product_type:
        domain.append(["type", "=", product_type])

    client = get_client()
    records = client.search_read(
        "product.product",
        domain=domain,
        fields=["name", "default_code", "type", "list_price", "qty_available", "categ_id"],
        limit=limit,
        order="name",
    )
    count = client.search_count("product.product", domain=domain)
    header = f"Products: showing {len(records)} of {count} total"
    return header + "\n\n" + _format_records(records)


# ---------------------------------------------------------------------------
# CRM Tools
# ---------------------------------------------------------------------------


@mcp.tool()
def get_leads(
    stage: str = "",
    salesperson: str = "",
    partner_name: str = "",
    lead_type: str = "",
    limit: int = 20,
) -> str:
    """Get CRM leads and opportunities.

    Args:
        stage: Filter by stage name (partial match, e.g. 'New', 'Qualified').
        salesperson: Filter by salesperson name (partial match).
        partner_name: Filter by customer/contact name (partial match).
        lead_type: Filter by type: 'lead' for leads, 'opportunity' for opportunities.
                   Leave empty for both.
        limit: Maximum number of results.
    """
    domain: list[Any] = []
    if stage:
        domain.append(["stage_id.name", "ilike", stage])
    if salesperson:
        domain.append(["user_id.name", "ilike", salesperson])
    if partner_name:
        domain.append(["partner_id.name", "ilike", partner_name])
    if lead_type:
        domain.append(["type", "=", lead_type])

    client = get_client()
    records = client.search_read(
        "crm.lead",
        domain=domain,
        fields=[
            "name", "partner_id", "user_id", "stage_id", "type",
            "expected_revenue", "probability", "date_deadline",
            "email_from", "phone",
        ],
        limit=limit,
        order="create_date desc",
    )
    count = client.search_count("crm.lead", domain=domain)
    header = f"CRM Leads/Opportunities: showing {len(records)} of {count} total"
    return header + "\n\n" + _format_records(records)


@mcp.tool()
def get_crm_pipeline_summary() -> str:
    """Get a summary of the CRM pipeline grouped by stage.

    Returns the number of leads/opportunities and total expected revenue per stage.
    """
    client = get_client()
    groups = client.read_group(
        "crm.lead",
        domain=[],
        fields=["stage_id", "expected_revenue"],
        groupby=["stage_id"],
    )
    if not groups:
        return "No CRM pipeline data found."
    lines = []
    for g in groups:
        stage = g.get("stage_id", [False, "Undefined"])
        stage_name = stage[1] if isinstance(stage, (list, tuple)) else str(stage)
        count = g.get("stage_id_count", 0)
        revenue = g.get("expected_revenue", 0)
        lines.append(f"- {stage_name}: {count} records, expected revenue: {revenue:,.2f}")
    return "CRM Pipeline Summary:\n" + "\n".join(lines)


# ---------------------------------------------------------------------------
# Purchase Tools
# ---------------------------------------------------------------------------


@mcp.tool()
def get_purchase_orders(
    state: str = "",
    partner_name: str = "",
    limit: int = 20,
) -> str:
    """Get purchase orders with common filters.

    Args:
        state: Filter by state (draft, sent, purchase, done, cancel). Leave empty for all.
        partner_name: Filter by vendor name (partial match).
        limit: Maximum number of results.
    """
    domain: list[Any] = []
    if state:
        domain.append(["state", "=", state])
    if partner_name:
        domain.append(["partner_id.name", "ilike", partner_name])

    client = get_client()
    records = client.search_read(
        "purchase.order",
        domain=domain,
        fields=[
            "name", "partner_id", "state", "date_order",
            "amount_total", "currency_id", "invoice_status",
        ],
        limit=limit,
        order="date_order desc",
    )
    count = client.search_count("purchase.order", domain=domain)
    header = f"Purchase Orders: showing {len(records)} of {count} total"
    return header + "\n\n" + _format_records(records)


# ---------------------------------------------------------------------------
# Inventory / Stock Tools
# ---------------------------------------------------------------------------


@mcp.tool()
def get_stock_pickings(
    picking_type: str = "",
    state: str = "",
    partner_name: str = "",
    limit: int = 20,
) -> str:
    """Get stock transfers/pickings (receipts, deliveries, internal transfers).

    Args:
        picking_type: Filter by operation type code: 'incoming' (receipts),
                      'outgoing' (deliveries), 'internal' (internal transfers).
                      Leave empty for all.
        state: Filter by state (draft, waiting, confirmed, assigned, done, cancel).
        partner_name: Filter by partner name (partial match).
        limit: Maximum number of results.
    """
    domain: list[Any] = []
    if picking_type:
        domain.append(["picking_type_code", "=", picking_type])
    if state:
        domain.append(["state", "=", state])
    if partner_name:
        domain.append(["partner_id.name", "ilike", partner_name])

    client = get_client()
    records = client.search_read(
        "stock.picking",
        domain=domain,
        fields=[
            "name", "partner_id", "picking_type_id", "picking_type_code",
            "state", "scheduled_date", "date_done", "origin",
        ],
        limit=limit,
        order="scheduled_date desc",
    )
    count = client.search_count("stock.picking", domain=domain)
    header = f"Stock Pickings: showing {len(records)} of {count} total"
    return header + "\n\n" + _format_records(records)


@mcp.tool()
def get_stock_quants(
    product_name: str = "",
    location_name: str = "",
    limit: int = 50,
) -> str:
    """Get current stock levels (quants) - how much of each product is in each location.

    Args:
        product_name: Filter by product name (partial match).
        location_name: Filter by stock location name (partial match).
        limit: Maximum number of results.
    """
    domain: list[Any] = [["quantity", ">", 0]]
    if product_name:
        domain.append(["product_id.name", "ilike", product_name])
    if location_name:
        domain.append(["location_id.complete_name", "ilike", location_name])

    client = get_client()
    records = client.search_read(
        "stock.quant",
        domain=domain,
        fields=[
            "product_id", "location_id", "quantity",
            "reserved_quantity", "available_quantity",
        ],
        limit=limit,
        order="product_id, location_id",
    )
    count = client.search_count("stock.quant", domain=domain)
    header = f"Stock Quants: showing {len(records)} of {count} total"
    return header + "\n\n" + _format_records(records)


@mcp.tool()
def get_warehouses() -> str:
    """List all warehouses configured in Odoo."""
    client = get_client()
    records = client.search_read(
        "stock.warehouse",
        domain=[],
        fields=["name", "code", "partner_id", "lot_stock_id"],
        order="name",
    )
    if not records:
        return "No warehouses found."
    return f"Warehouses ({len(records)}):\n\n" + _format_records(records)


@mcp.tool()
def get_stock_moves(
    product_name: str = "",
    state: str = "",
    limit: int = 20,
) -> str:
    """Get stock moves (individual product movements between locations).

    Args:
        product_name: Filter by product name (partial match).
        state: Filter by state (draft, waiting, confirmed, partially_available,
               assigned, done, cancel).
        limit: Maximum number of results.
    """
    domain: list[Any] = []
    if product_name:
        domain.append(["product_id.name", "ilike", product_name])
    if state:
        domain.append(["state", "=", state])

    client = get_client()
    records = client.search_read(
        "stock.move",
        domain=domain,
        fields=[
            "product_id", "product_uom_qty", "quantity",
            "location_id", "location_dest_id", "state",
            "date", "origin", "reference",
        ],
        limit=limit,
        order="date desc",
    )
    count = client.search_count("stock.move", domain=domain)
    header = f"Stock Moves: showing {len(records)} of {count} total"
    return header + "\n\n" + _format_records(records)


# ---------------------------------------------------------------------------
# Accounting Tools
# ---------------------------------------------------------------------------


@mcp.tool()
def get_payments(
    payment_type: str = "",
    partner_name: str = "",
    state: str = "",
    limit: int = 20,
) -> str:
    """Get payments (customer payments and vendor payments).

    Args:
        payment_type: 'inbound' for customer payments, 'outbound' for vendor payments.
                      Leave empty for all.
        partner_name: Filter by partner name (partial match).
        state: Filter by state (draft, posted, cancel).
        limit: Maximum number of results.
    """
    domain: list[Any] = []
    if payment_type:
        domain.append(["payment_type", "=", payment_type])
    if partner_name:
        domain.append(["partner_id.name", "ilike", partner_name])
    if state:
        domain.append(["state", "=", state])

    client = get_client()
    records = client.search_read(
        "account.payment",
        domain=domain,
        fields=[
            "name", "partner_id", "payment_type", "amount",
            "currency_id", "date", "state", "journal_id", "ref",
        ],
        limit=limit,
        order="date desc",
    )
    count = client.search_count("account.payment", domain=domain)
    header = f"Payments: showing {len(records)} of {count} total"
    return header + "\n\n" + _format_records(records)


@mcp.tool()
def get_journal_entries(
    journal_name: str = "",
    state: str = "",
    date_from: str = "",
    date_to: str = "",
    limit: int = 20,
) -> str:
    """Get journal entries (account.move that are not invoices).

    Args:
        journal_name: Filter by journal name (partial match).
        state: Filter by state (draft, posted).
        date_from: Filter entries from this date (YYYY-MM-DD).
        date_to: Filter entries until this date (YYYY-MM-DD).
        limit: Maximum number of results.
    """
    domain: list[Any] = [["move_type", "=", "entry"]]
    if journal_name:
        domain.append(["journal_id.name", "ilike", journal_name])
    if state:
        domain.append(["state", "=", state])
    if date_from:
        domain.append(["date", ">=", date_from])
    if date_to:
        domain.append(["date", "<=", date_to])

    client = get_client()
    records = client.search_read(
        "account.move",
        domain=domain,
        fields=[
            "name", "journal_id", "date", "state",
            "amount_total", "ref", "partner_id",
        ],
        limit=limit,
        order="date desc",
    )
    count = client.search_count("account.move", domain=domain)
    header = f"Journal Entries: showing {len(records)} of {count} total"
    return header + "\n\n" + _format_records(records)


@mcp.tool()
def get_journal_items(
    account_code: str = "",
    partner_name: str = "",
    date_from: str = "",
    date_to: str = "",
    limit: int = 30,
) -> str:
    """Get journal items (account.move.line) - individual debit/credit lines.

    Args:
        account_code: Filter by account code (e.g. '4000', '1100'). Partial match.
        partner_name: Filter by partner name (partial match).
        date_from: Filter from this date (YYYY-MM-DD).
        date_to: Filter until this date (YYYY-MM-DD).
        limit: Maximum number of results.
    """
    domain: list[Any] = []
    if account_code:
        domain.append(["account_id.code", "ilike", account_code])
    if partner_name:
        domain.append(["partner_id.name", "ilike", partner_name])
    if date_from:
        domain.append(["date", ">=", date_from])
    if date_to:
        domain.append(["date", "<=", date_to])

    client = get_client()
    records = client.search_read(
        "account.move.line",
        domain=domain,
        fields=[
            "move_id", "account_id", "partner_id", "name",
            "debit", "credit", "balance", "date", "journal_id",
        ],
        limit=limit,
        order="date desc",
    )
    count = client.search_count("account.move.line", domain=domain)
    header = f"Journal Items: showing {len(records)} of {count} total"
    return header + "\n\n" + _format_records(records)


@mcp.tool()
def get_account_balances(
    account_type: str = "",
    code_prefix: str = "",
) -> str:
    """Get account balances grouped by account.

    Useful for a quick trial balance or checking specific account balances.

    Args:
        account_type: Filter by account type (e.g. 'asset_receivable', 'liability_payable',
                      'income', 'expense', 'asset_cash', 'equity'). Leave empty for all.
        code_prefix: Filter accounts whose code starts with this prefix (e.g. '4' for revenue).
    """
    domain: list[Any] = []
    if account_type:
        domain.append(["account_id.account_type", "=", account_type])
    if code_prefix:
        domain.append(["account_id.code", "=like", f"{code_prefix}%"])

    client = get_client()
    groups = client.read_group(
        "account.move.line",
        domain=domain,
        fields=["account_id", "debit", "credit", "balance"],
        groupby=["account_id"],
    )
    if not groups:
        return "No account data found."

    lines = []
    for g in groups:
        acc = g.get("account_id", [False, "Unknown"])
        acc_name = acc[1] if isinstance(acc, (list, tuple)) else str(acc)
        debit = g.get("debit", 0)
        credit = g.get("credit", 0)
        balance = g.get("balance", 0)
        lines.append(f"- {acc_name}: debit={debit:,.2f}  credit={credit:,.2f}  balance={balance:,.2f}")

    return f"Account Balances ({len(lines)} accounts):\n" + "\n".join(lines)


# ---------------------------------------------------------------------------
# HR Tools
# ---------------------------------------------------------------------------


@mcp.tool()
def get_employees(
    name: str = "",
    department: str = "",
    job_title: str = "",
    limit: int = 30,
) -> str:
    """Get employees with common filters.

    Args:
        name: Filter by employee name (partial match).
        department: Filter by department name (partial match).
        job_title: Filter by job title (partial match).
        limit: Maximum number of results.
    """
    domain: list[Any] = []
    if name:
        domain.append(["name", "ilike", name])
    if department:
        domain.append(["department_id.name", "ilike", department])
    if job_title:
        domain.append(["job_title", "ilike", job_title])

    client = get_client()
    records = client.search_read(
        "hr.employee",
        domain=domain,
        fields=[
            "name", "job_title", "department_id", "parent_id",
            "work_email", "work_phone", "company_id",
        ],
        limit=limit,
        order="name",
    )
    count = client.search_count("hr.employee", domain=domain)
    header = f"Employees: showing {len(records)} of {count} total"
    return header + "\n\n" + _format_records(records)


@mcp.tool()
def get_departments() -> str:
    """List all departments in the organization."""
    client = get_client()
    records = client.search_read(
        "hr.department",
        domain=[],
        fields=["name", "manager_id", "parent_id", "company_id", "total_employee"],
        order="name",
    )
    if not records:
        return "No departments found."
    return f"Departments ({len(records)}):\n\n" + _format_records(records)


@mcp.tool()
def get_leaves(
    employee_name: str = "",
    state: str = "",
    date_from: str = "",
    limit: int = 20,
) -> str:
    """Get employee leave/time-off requests.

    Args:
        employee_name: Filter by employee name (partial match).
        state: Filter by state (draft, confirm, validate1, validate, refuse).
        date_from: Filter leaves starting from this date (YYYY-MM-DD).
        limit: Maximum number of results.
    """
    domain: list[Any] = []
    if employee_name:
        domain.append(["employee_id.name", "ilike", employee_name])
    if state:
        domain.append(["state", "=", state])
    if date_from:
        domain.append(["date_from", ">=", date_from])

    client = get_client()
    records = client.search_read(
        "hr.leave",
        domain=domain,
        fields=[
            "employee_id", "holiday_status_id", "date_from", "date_to",
            "number_of_days", "state", "name",
        ],
        limit=limit,
        order="date_from desc",
    )
    count = client.search_count("hr.leave", domain=domain)
    header = f"Leaves: showing {len(records)} of {count} total"
    return header + "\n\n" + _format_records(records)


# ---------------------------------------------------------------------------
# Project Tools
# ---------------------------------------------------------------------------


@mcp.tool()
def get_projects(
    name: str = "",
    manager: str = "",
    limit: int = 20,
) -> str:
    """Get projects.

    Args:
        name: Filter by project name (partial match).
        manager: Filter by project manager name (partial match).
        limit: Maximum number of results.
    """
    domain: list[Any] = []
    if name:
        domain.append(["name", "ilike", name])
    if manager:
        domain.append(["user_id.name", "ilike", manager])

    client = get_client()
    records = client.search_read(
        "project.project",
        domain=domain,
        fields=[
            "name", "user_id", "partner_id", "date_start",
            "date", "task_count", "company_id",
        ],
        limit=limit,
        order="name",
    )
    count = client.search_count("project.project", domain=domain)
    header = f"Projects: showing {len(records)} of {count} total"
    return header + "\n\n" + _format_records(records)


@mcp.tool()
def get_tasks(
    project_name: str = "",
    assignee: str = "",
    stage: str = "",
    priority: str = "",
    limit: int = 20,
) -> str:
    """Get project tasks.

    Args:
        project_name: Filter by project name (partial match).
        assignee: Filter by assigned user name (partial match).
        stage: Filter by stage name (partial match, e.g. 'In Progress', 'Done').
        priority: Filter by priority: '0' (normal), '1' (important/starred).
        limit: Maximum number of results.
    """
    domain: list[Any] = []
    if project_name:
        domain.append(["project_id.name", "ilike", project_name])
    if assignee:
        domain.append(["user_ids.name", "ilike", assignee])
    if stage:
        domain.append(["stage_id.name", "ilike", stage])
    if priority:
        domain.append(["priority", "=", priority])

    client = get_client()
    records = client.search_read(
        "project.task",
        domain=domain,
        fields=[
            "name", "project_id", "user_ids", "stage_id",
            "priority", "date_deadline", "tag_ids",
        ],
        limit=limit,
        order="priority desc, date_deadline asc",
    )
    count = client.search_count("project.task", domain=domain)
    header = f"Tasks: showing {len(records)} of {count} total"
    return header + "\n\n" + _format_records(records)


# ---------------------------------------------------------------------------
# Manufacturing Tools
# ---------------------------------------------------------------------------


@mcp.tool()
def get_manufacturing_orders(
    product_name: str = "",
    state: str = "",
    limit: int = 20,
) -> str:
    """Get manufacturing/production orders (MRP).

    Args:
        product_name: Filter by product name (partial match).
        state: Filter by state (draft, confirmed, progress, to_close, done, cancel).
        limit: Maximum number of results.
    """
    domain: list[Any] = []
    if product_name:
        domain.append(["product_id.name", "ilike", product_name])
    if state:
        domain.append(["state", "=", state])

    client = get_client()
    records = client.search_read(
        "mrp.production",
        domain=domain,
        fields=[
            "name", "product_id", "product_qty", "product_uom_id",
            "state", "date_start", "date_finished", "origin",
        ],
        limit=limit,
        order="date_start desc",
    )
    count = client.search_count("mrp.production", domain=domain)
    header = f"Manufacturing Orders: showing {len(records)} of {count} total"
    return header + "\n\n" + _format_records(records)


@mcp.tool()
def get_bill_of_materials(
    product_name: str = "",
    limit: int = 20,
) -> str:
    """Get Bills of Materials (BoM).

    Args:
        product_name: Filter by product name (partial match).
        limit: Maximum number of results.
    """
    domain: list[Any] = []
    if product_name:
        domain.append(["product_tmpl_id.name", "ilike", product_name])

    client = get_client()
    records = client.search_read(
        "mrp.bom",
        domain=domain,
        fields=[
            "product_tmpl_id", "product_qty", "product_uom_id",
            "type", "code", "bom_line_ids",
        ],
        limit=limit,
        order="product_tmpl_id",
    )
    count = client.search_count("mrp.bom", domain=domain)
    header = f"Bills of Materials: showing {len(records)} of {count} total"
    return header + "\n\n" + _format_records(records)


# ---------------------------------------------------------------------------
# Utility Tools
# ---------------------------------------------------------------------------


@mcp.tool()
def get_company_info() -> str:
    """Get information about the current company."""
    client = get_client()
    user = client.read("res.users", [client.uid], fields=["company_id"])
    if not user:
        return "Could not determine current company."
    company_id = user[0]["company_id"][0]
    company = client.read(
        "res.company",
        [company_id],
        fields=[
            "name", "street", "city", "state_id", "country_id", "zip",
            "phone", "email", "website", "vat", "currency_id",
        ],
    )
    if not company:
        return "Company not found."
    return json.dumps(company[0], indent=2, default=str, ensure_ascii=False)


@mcp.tool()
def get_users(active_only: bool = True, limit: int = 50) -> str:
    """List Odoo users.

    Args:
        active_only: If True, only show active users (default True).
        limit: Maximum number of results.
    """
    domain: list[Any] = []
    if active_only:
        domain.append(["active", "=", True])

    client = get_client()
    records = client.search_read(
        "res.users",
        domain=domain,
        fields=["name", "login", "email", "company_id", "groups_id"],
        limit=limit,
        order="name",
    )
    count = client.search_count("res.users", domain=domain)
    header = f"Users: showing {len(records)} of {count} total"
    return header + "\n\n" + _format_records(records)


@mcp.tool()
def get_chatter_messages(
    model: str,
    record_id: int,
    limit: int = 20,
) -> str:
    """Get chatter messages (mail.message) for a specific record.

    This retrieves the discussion/log messages attached to any Odoo record
    (e.g. notes on a sale order, comments on a task).

    Args:
        model: The model of the record (e.g. 'sale.order', 'res.partner').
        record_id: The ID of the record.
        limit: Maximum number of messages to retrieve.
    """
    client = get_client()
    domain: list[Any] = [
        ["model", "=", model],
        ["res_id", "=", record_id],
    ]
    records = client.search_read(
        "mail.message",
        domain=domain,
        fields=["date", "author_id", "body", "message_type", "subtype_id"],
        limit=limit,
        order="date desc",
    )
    if not records:
        return f"No messages found for {model} ID {record_id}."
    header = f"Messages for {model} #{record_id} ({len(records)} messages):"
    return header + "\n\n" + _format_records(records)


@mcp.tool()
def get_activities(
    model: str = "",
    user_name: str = "",
    overdue_only: bool = False,
    limit: int = 20,
) -> str:
    """Get scheduled activities (to-dos, calls, meetings, etc.).

    Args:
        model: Filter by model (e.g. 'sale.order', 'crm.lead'). Leave empty for all.
        user_name: Filter by assigned user name (partial match).
        overdue_only: If True, only show overdue activities.
        limit: Maximum number of results.
    """
    domain: list[Any] = []
    if model:
        domain.append(["res_model", "=", model])
    if user_name:
        domain.append(["user_id.name", "ilike", user_name])
    if overdue_only:
        from datetime import date
        domain.append(["date_deadline", "<", date.today().isoformat()])

    client = get_client()
    records = client.search_read(
        "mail.activity",
        domain=domain,
        fields=[
            "res_model", "res_id", "res_name", "activity_type_id",
            "summary", "date_deadline", "user_id", "state",
        ],
        limit=limit,
        order="date_deadline asc",
    )
    count = client.search_count("mail.activity", domain=domain)
    header = f"Activities: showing {len(records)} of {count} total"
    return header + "\n\n" + _format_records(records)


@mcp.tool()
def read_group_data(
    model: str,
    domain: str = "[]",
    fields: str = "",
    groupby: str = "",
    limit: int = 50,
) -> str:
    """Read aggregated/grouped data from any model (like SQL GROUP BY).

    This is very powerful for analytics and reporting. It returns sums,
    counts, and averages grouped by specified fields.

    Args:
        model: The technical model name (e.g. 'sale.order').
        domain: Odoo domain filter as JSON string.
        fields: Comma-separated fields to aggregate (e.g. 'amount_total,state').
                Include the groupby field and any numeric fields to sum.
        groupby: Comma-separated fields to group by (e.g. 'state', 'partner_id,state').
        limit: Maximum number of groups to return.
    """
    client = get_client()
    parsed_domain = json.loads(domain)
    field_list = [f.strip() for f in fields.split(",") if f.strip()] if fields else []
    group_list = [f.strip() for f in groupby.split(",") if f.strip()] if groupby else []

    if not group_list:
        return "Error: groupby is required. Specify at least one field to group by."

    groups = client.read_group(
        model,
        domain=parsed_domain,
        fields=field_list,
        groupby=group_list,
        limit=limit,
    )
    if not groups:
        return f"No grouped data found for '{model}'."
    return f"Grouped data for '{model}' ({len(groups)} groups):\n\n" + json.dumps(
        groups, indent=2, default=str, ensure_ascii=False
    )


@mcp.tool()
def bulk_create_records(model: str, records_json: str) -> str:
    """Create multiple records at once in an Odoo model.

    Args:
        model: The technical model name (e.g. 'res.partner').
        records_json: JSON array of objects, each containing field values. Example:
                      '[{"name": "Alice", "email": "alice@example.com"},
                        {"name": "Bob", "email": "bob@example.com"}]'
    """
    client = get_client()
    values_list = json.loads(records_json)
    if not isinstance(values_list, list):
        return "Error: records_json must be a JSON array of objects."
    ids = client.create_multi(model, values_list)
    return f"Created {len(ids)} records in '{model}'. IDs: {ids}"


@mcp.tool()
def bulk_update_records(model: str, record_ids: str, values: str) -> str:
    """Update multiple records at once in an Odoo model.

    Args:
        model: The technical model name (e.g. 'res.partner').
        record_ids: JSON array of record IDs to update (e.g. '[1, 2, 3]').
        values: JSON object with field values to set on all records. Example:
                '{"active": false}'
    """
    client = get_client()
    ids = json.loads(record_ids)
    parsed_values = json.loads(values)
    client.write(model, ids, parsed_values)
    return f"Updated {len(ids)} records in '{model}'."


@mcp.tool()
def get_default_values(model: str, fields: str) -> str:
    """Get default values for fields when creating a new record.

    Useful to understand what defaults Odoo would pre-fill.

    Args:
        model: The technical model name (e.g. 'sale.order').
        fields: Comma-separated list of field names.
    """
    client = get_client()
    field_list = [f.strip() for f in fields.split(",") if f.strip()]
    defaults = client.default_get(model, field_list)
    return f"Default values for '{model}':\n" + json.dumps(
        defaults, indent=2, default=str, ensure_ascii=False
    )


@mcp.tool()
def get_installed_modules(filter_name: str = "", state: str = "installed") -> str:
    """List installed (or available) Odoo modules.

    Args:
        filter_name: Filter by module name (partial match).
        state: Filter by state: 'installed', 'uninstalled', 'to upgrade'.
               Leave empty for all states.
    """
    domain: list[Any] = []
    if filter_name:
        domain.append(["name", "ilike", filter_name])
    if state:
        domain.append(["state", "=", state])

    client = get_client()
    records = client.search_read(
        "ir.module.module",
        domain=domain,
        fields=["name", "shortdesc", "state", "installed_version", "author"],
        limit=100,
        order="name",
    )
    count = client.search_count("ir.module.module", domain=domain)
    header = f"Modules: showing {len(records)} of {count} total"
    return header + "\n\n" + _format_records(records)


@mcp.tool()
def get_sale_order_lines(
    order_name: str = "",
    product_name: str = "",
    limit: int = 30,
) -> str:
    """Get sale order lines (the detail lines inside sales orders).

    Args:
        order_name: Filter by order reference/name (e.g. 'SO001'). Partial match.
        product_name: Filter by product name (partial match).
        limit: Maximum number of results.
    """
    domain: list[Any] = []
    if order_name:
        domain.append(["order_id.name", "ilike", order_name])
    if product_name:
        domain.append(["product_id.name", "ilike", product_name])

    client = get_client()
    records = client.search_read(
        "sale.order.line",
        domain=domain,
        fields=[
            "order_id", "product_id", "name", "product_uom_qty",
            "price_unit", "discount", "price_subtotal", "price_total",
        ],
        limit=limit,
        order="order_id desc",
    )
    count = client.search_count("sale.order.line", domain=domain)
    header = f"Sale Order Lines: showing {len(records)} of {count} total"
    return header + "\n\n" + _format_records(records)


@mcp.tool()
def get_invoice_lines(
    invoice_name: str = "",
    account_code: str = "",
    limit: int = 30,
) -> str:
    """Get invoice lines (the detail lines inside invoices/bills).

    Args:
        invoice_name: Filter by invoice reference (e.g. 'INV/2024/0001'). Partial match.
        account_code: Filter by account code (partial match).
        limit: Maximum number of results.
    """
    domain: list[Any] = [["display_type", "=", "product"]]
    if invoice_name:
        domain.append(["move_id.name", "ilike", invoice_name])
    if account_code:
        domain.append(["account_id.code", "ilike", account_code])

    client = get_client()
    records = client.search_read(
        "account.move.line",
        domain=domain,
        fields=[
            "move_id", "product_id", "name", "quantity",
            "price_unit", "discount", "price_subtotal", "price_total",
            "account_id",
        ],
        limit=limit,
        order="move_id desc",
    )
    count = client.search_count("account.move.line", domain=domain)
    header = f"Invoice Lines: showing {len(records)} of {count} total"
    return header + "\n\n" + _format_records(records)


@mcp.tool()
def get_pos_orders(
    session_name: str = "",
    partner_name: str = "",
    state: str = "",
    date_from: str = "",
    limit: int = 20,
) -> str:
    """Get Point of Sale orders.

    Args:
        session_name: Filter by POS session name (partial match).
        partner_name: Filter by customer name (partial match).
        state: Filter by state (draft, paid, done, invoiced, cancel).
        date_from: Filter orders from this date (YYYY-MM-DD).
        limit: Maximum number of results.
    """
    domain: list[Any] = []
    if session_name:
        domain.append(["session_id.name", "ilike", session_name])
    if partner_name:
        domain.append(["partner_id.name", "ilike", partner_name])
    if state:
        domain.append(["state", "=", state])
    if date_from:
        domain.append(["date_order", ">=", date_from])

    client = get_client()
    records = client.search_read(
        "pos.order",
        domain=domain,
        fields=[
            "name", "partner_id", "session_id", "date_order",
            "amount_total", "amount_paid", "state",
        ],
        limit=limit,
        order="date_order desc",
    )
    count = client.search_count("pos.order", domain=domain)
    header = f"POS Orders: showing {len(records)} of {count} total"
    return header + "\n\n" + _format_records(records)


@mcp.tool()
def get_contacts_with_overdue_invoices() -> str:
    """Get contacts that have overdue invoices (unpaid and past due date).

    Useful for collections and accounts receivable management.
    """
    from datetime import date

    client = get_client()
    domain: list[Any] = [
        ["move_type", "=", "out_invoice"],
        ["state", "=", "posted"],
        ["amount_residual", ">", 0],
        ["invoice_date_due", "<", date.today().isoformat()],
    ]
    groups = client.read_group(
        "account.move",
        domain=domain,
        fields=["partner_id", "amount_residual"],
        groupby=["partner_id"],
    )
    if not groups:
        return "No overdue invoices found."
    lines = []
    for g in groups:
        partner = g.get("partner_id", [False, "Unknown"])
        partner_name = partner[1] if isinstance(partner, (list, tuple)) else str(partner)
        amount = g.get("amount_residual", 0)
        count = g.get("partner_id_count", 0)
        lines.append(f"- {partner_name}: {count} overdue invoices, total due: {amount:,.2f}")
    return f"Contacts with Overdue Invoices ({len(lines)}):\n" + "\n".join(lines)


@mcp.tool()
def get_sales_summary(
    date_from: str = "",
    date_to: str = "",
    group_by: str = "partner_id",
) -> str:
    """Get a sales summary grouped by a dimension.

    Args:
        date_from: Start date (YYYY-MM-DD). Leave empty for all time.
        date_to: End date (YYYY-MM-DD). Leave empty for today.
        group_by: Dimension to group by: 'partner_id' (customer), 'user_id' (salesperson),
                  'state' (order status). Default: 'partner_id'.
    """
    domain: list[Any] = []
    if date_from:
        domain.append(["date_order", ">=", date_from])
    if date_to:
        domain.append(["date_order", "<=", date_to])

    client = get_client()
    groups = client.read_group(
        "sale.order",
        domain=domain,
        fields=[group_by, "amount_total"],
        groupby=[group_by],
    )
    if not groups:
        return "No sales data found for the given filters."

    lines = []
    for g in groups:
        key = g.get(group_by, "Unknown")
        if isinstance(key, (list, tuple)):
            key = key[1]
        amount = g.get("amount_total", 0)
        count = g.get(f"{group_by}_count", 0)
        lines.append(f"- {key}: {count} orders, total: {amount:,.2f}")
    return f"Sales Summary by {group_by} ({len(lines)} groups):\n" + "\n".join(lines)


# ---------------------------------------------------------------------------
# Resources
# ---------------------------------------------------------------------------


@mcp.resource("odoo://info")
def odoo_info() -> str:
    """General information about the connected Odoo instance."""
    try:
        client = get_client()
        version = client.server_version()
        return json.dumps(
            {
                "url": client.config.base_url,
                "database": client.config.db,
                "version": version,
                "uid": client.uid,
            },
            indent=2,
        )
    except Exception as e:
        return f"Error connecting to Odoo: {e}"


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------


@mcp.prompt()
def explore_model(model: str) -> str:
    """Generate a prompt to explore an Odoo model's structure and data."""
    return (
        f"I want to explore the Odoo model '{model}'. Please:\n"
        f"1. Use get_model_fields to see all fields of '{model}'\n"
        f"2. Use search_records to show me the first 5 records\n"
        f"3. Summarize the model structure and current data"
    )


@mcp.prompt()
def analyze_sales() -> str:
    """Generate a prompt to analyze sales data."""
    return (
        "Please analyze the sales data in Odoo:\n"
        "1. Use get_sales_orders to get recent orders\n"
        "2. Use get_sales_summary with group_by='state' to see orders by status\n"
        "3. Use get_sales_summary with group_by='partner_id' to identify top customers\n"
        "4. Provide a summary of sales performance"
    )


@mcp.prompt()
def analyze_inventory(product: str = "") -> str:
    """Generate a prompt to analyze inventory levels."""
    product_filter = f" for product '{product}'" if product else ""
    return (
        f"Please analyze the inventory{product_filter} in Odoo:\n"
        f"1. Use get_stock_quants to check current stock levels{product_filter}\n"
        "2. Use get_warehouses to list available warehouses\n"
        "3. Use get_stock_pickings with state='assigned' to see pending transfers\n"
        "4. Summarize stock availability and any issues"
    )


@mcp.prompt()
def analyze_receivables() -> str:
    """Generate a prompt to analyze accounts receivable."""
    return (
        "Please analyze accounts receivable in Odoo:\n"
        "1. Use get_contacts_with_overdue_invoices to find overdue debts\n"
        "2. Use get_invoices with state='posted' to see open invoices\n"
        "3. Use get_payments with payment_type='inbound' to see recent payments\n"
        "4. Provide a summary of the AR situation and recommendations"
    )


@mcp.prompt()
def daily_overview() -> str:
    """Generate a prompt for a daily business overview."""
    return (
        "Please give me a daily business overview from Odoo:\n"
        "1. Use get_activities with overdue_only=True to check overdue activities\n"
        "2. Use get_sales_orders with state='draft' to see pending quotations\n"
        "3. Use get_stock_pickings with state='assigned' to see ready deliveries\n"
        "4. Use get_contacts_with_overdue_invoices for collections follow-up\n"
        "5. Summarize key actions needed today"
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Run the MCP server."""
    logger.info("Starting Odoo 18 MCP Server...")
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
