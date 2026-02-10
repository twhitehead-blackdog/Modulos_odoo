{
    "name": "Respond.io CRM Bridge",
    "version": "18.0.1.0.0",
    "category": "Sales/CRM",
    "summary": "Integrates respond.io messaging with Odoo CRM via webhooks and API",
    "description": """
        respond.io CRM Bridge
        ======================
        Bridges respond.io (messaging) with Odoo CRM.

        respond.io remains the owner of conversations (inbox, assignments, tags).
        Odoo remains the owner of CRM (leads, opportunities, contacts, pipeline).

        Features:
        - Receives respond.io webhook events (messages, contacts, conversations)
        - Creates/updates leads, contacts, and activities in Odoo
        - Deep-link buttons to open conversations in respond.io
        - Idempotent event processing with full audit log
        - Optional outbound messaging via respond.io API
    """,
    "author": "Black Dog Panama",
    "website": "https://github.com/twhitehead-blackdog/Modulos_odoo",
    "license": "LGPL-3",
    "depends": [
        "base",
        "crm",
        "mail",
        "contacts",
    ],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "views/respondio_account_views.xml",
        "views/respondio_conversation_views.xml",
        "views/respondio_event_log_views.xml",
        "views/crm_lead_views.xml",
        "views/res_partner_views.xml",
        "views/respondio_send_message_wizard_views.xml",
        "views/menu.xml",
        "data/cron.xml",
        "data/server_actions.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
