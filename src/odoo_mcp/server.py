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
        "2. Count total orders by state\n"
        "3. Identify the top customers\n"
        "4. Provide a summary of sales performance"
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
