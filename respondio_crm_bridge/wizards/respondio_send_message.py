"""Wizard to send an outbound message via respond.io from Odoo."""

import logging

from odoo import fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class RespondioSendMessageWizard(models.TransientModel):
    _name = "respondio.send.message.wizard"
    _description = "Send Message via Respond.io"

    lead_id = fields.Many2one("crm.lead", string="Lead")
    respondio_contact_id = fields.Many2one(
        "respondio.contact", string="Respond.io Contact", required=True
    )
    account_id = fields.Many2one(
        "respondio.account", string="Account", required=True
    )
    message = fields.Text(string="Message", required=True)

    def action_send(self):
        self.ensure_one()
        if not self.account_id.enable_outbound_messages:
            raise UserError(
                "Outbound messages are disabled for this respond.io account. "
                "Enable them in the account settings."
            )
        from ..services.respondio_api import RespondioAPI

        api = RespondioAPI(self.account_id)
        try:
            api.send_text_message(
                self.respondio_contact_id.respondio_id,
                self.message,
            )
        except Exception as exc:
            raise UserError(f"Failed to send message: {exc}") from exc

        # Log in chatter
        if self.lead_id:
            self.lead_id.message_post(
                body=f"Outbound message sent via respond.io: {self.message}",
                message_type="comment",
                subtype_xmlid="mail.mt_note",
            )
        return {"type": "ir.actions.act_window_close"}
