import logging

from odoo import api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class RespondioAccount(models.Model):
    _name = "respondio.account"
    _description = "Respond.io Account"
    _order = "name"

    name = fields.Char(required=True)
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
    )
    api_base_url = fields.Char(
        string="API Base URL",
        required=True,
        default="https://api.respond.io/api/v2",
        help="Base URL for the respond.io API (e.g. https://api.respond.io/api/v2)",
    )
    api_token = fields.Char(
        string="API Token",
        required=True,
        groups="respondio_crm_bridge.group_respondio_admin",
        help="Bearer token for respond.io API authentication",
    )
    webhook_secret = fields.Char(
        string="Webhook Secret",
        groups="respondio_crm_bridge.group_respondio_admin",
        help="Secret used to validate incoming webhook signatures (HMAC)",
    )
    active = fields.Boolean(default=True)
    last_sync_at = fields.Datetime(string="Last Sync", readonly=True)
    default_team_id = fields.Many2one(
        "crm.team",
        string="Default Sales Team",
        help="Sales team assigned to leads created from this account",
    )
    default_user_id = fields.Many2one(
        "res.users",
        string="Default Salesperson",
        help="Fallback salesperson for leads when no mapping exists",
    )
    default_lead_stage_id = fields.Many2one(
        "crm.stage",
        string="Default Lead Stage",
        help="Stage assigned to new leads (defaults to first stage if empty)",
    )
    create_partner_on_new_contact = fields.Boolean(
        string="Auto-create Partner",
        default=True,
        help="Automatically create a res.partner when a new respond.io contact arrives",
    )
    enable_outbound_messages = fields.Boolean(
        string="Enable Outbound Messages",
        default=False,
        help="Allow sending messages to respond.io from Odoo",
    )
    enable_push_partner_updates = fields.Boolean(
        string="Push Partner Updates",
        default=False,
        help="Push partner data changes back to respond.io",
    )
    auto_create_activity_on_inbound = fields.Boolean(
        string="Auto-create Activity on Inbound",
        default=True,
        help="Create a follow-up activity when a new inbound message arrives",
    )
    activity_type_id = fields.Many2one(
        "mail.activity.type",
        string="Activity Type",
        help="Type of activity to create for follow-ups",
    )
    activity_delay_hours = fields.Integer(
        string="Activity Delay (hours)",
        default=24,
        help="Hours from now to schedule the follow-up activity deadline",
    )
    respondio_space_url = fields.Char(
        string="Respond.io Space URL",
        help="Base URL for deep-links (e.g. https://app.respond.io/space/12345)",
    )

    # ---- Computed / stats ----
    contact_count = fields.Integer(compute="_compute_counts")
    conversation_count = fields.Integer(compute="_compute_counts")
    event_count = fields.Integer(compute="_compute_counts")

    def _compute_counts(self):
        for rec in self:
            rec.contact_count = self.env["respondio.contact"].search_count(
                [("account_id", "=", rec.id)]
            )
            rec.conversation_count = self.env["respondio.conversation"].search_count(
                [("account_id", "=", rec.id)]
            )
            rec.event_count = self.env["respondio.event.log"].search_count(
                [("account_id", "=", rec.id)]
            )

    # ---- Actions ----
    def action_test_connection(self):
        """Test the API connection to respond.io."""
        self.ensure_one()
        from ..services.respondio_api import RespondioAPI

        api = RespondioAPI(self)
        try:
            api.test_connection()
        except Exception as exc:
            raise UserError(f"Connection failed: {exc}") from exc
        raise UserError("Connection successful!")  # simple feedback via dialog

    def action_view_contacts(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Respond.io Contacts",
            "res_model": "respondio.contact",
            "view_mode": "list,form",
            "domain": [("account_id", "=", self.id)],
        }

    def action_view_conversations(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Conversations",
            "res_model": "respondio.conversation",
            "view_mode": "list,form",
            "domain": [("account_id", "=", self.id)],
        }

    def action_view_events(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Event Log",
            "res_model": "respondio.event.log",
            "view_mode": "list,form",
            "domain": [("account_id", "=", self.id)],
        }
