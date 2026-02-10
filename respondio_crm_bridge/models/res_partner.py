import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = "res.partner"

    respondio_contact_id = fields.Many2one(
        "respondio.contact",
        string="Respond.io Contact",
        index=True,
    )
    respondio_last_seen_at = fields.Datetime(string="Last Seen (respond.io)")
    respondio_tags = fields.Char(string="Respond.io Tags")
    respondio_url = fields.Char(
        string="Respond.io URL",
        help="Deep-link to the contact profile in respond.io",
    )

    def action_open_in_respondio(self):
        self.ensure_one()
        if not self.respondio_url:
            return
        return {
            "type": "ir.actions.act_url",
            "url": self.respondio_url,
            "target": "new",
        }

    def action_create_opportunity_from_respondio(self):
        """Create a CRM lead/opportunity from this partner's respond.io data."""
        self.ensure_one()
        contact = self.respondio_contact_id
        if not contact:
            return

        conversation = self.env["respondio.conversation"].search(
            [("respondio_contact_id", "=", contact.id)],
            order="last_message_at desc",
            limit=1,
        )
        account = contact.account_id
        vals = {
            "name": f"{self.name} - {contact.channel or 'respond.io'}",
            "partner_id": self.id,
            "respondio_contact_id": contact.id,
            "respondio_channel": contact.channel,
            "respondio_tags": contact.tags,
        }
        if conversation:
            vals["respondio_conversation_id"] = conversation.id
            vals["respondio_last_message_at"] = conversation.last_message_at
            vals["respondio_assignee_name"] = conversation.assignee_name
        if account.default_team_id:
            vals["team_id"] = account.default_team_id.id
        if account.default_user_id:
            vals["user_id"] = account.default_user_id.id

        lead = self.env["crm.lead"].create(vals)
        if conversation:
            conversation.lead_id = lead.id
        return {
            "type": "ir.actions.act_window",
            "res_model": "crm.lead",
            "res_id": lead.id,
            "view_mode": "form",
        }
