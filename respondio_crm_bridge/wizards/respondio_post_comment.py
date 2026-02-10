"""Wizard to post an internal comment on a respond.io contact."""

import logging

from odoo import fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class RespondioPostCommentWizard(models.TransientModel):
    _name = "respondio.post.comment.wizard"
    _description = "Post Comment to Respond.io"

    lead_id = fields.Many2one("crm.lead", string="Lead")
    respondio_contact_id = fields.Many2one(
        "respondio.contact", string="Respond.io Contact", required=True
    )
    account_id = fields.Many2one(
        "respondio.account", string="Account", required=True
    )
    text = fields.Text(
        string="Comment",
        required=True,
        help="Max 1000 characters. Use {{@user.ID}} to mention users, "
             "{{$contact.name}} for dynamic variables.",
    )

    def action_post(self):
        self.ensure_one()
        from ..services.respondio_api import RespondioAPI

        api = RespondioAPI(self.account_id)
        try:
            api.create_comment(
                respondio_id=self.respondio_contact_id.respondio_id,
                text=self.text,
            )
        except Exception as exc:
            raise UserError(f"Failed to post comment: {exc}") from exc

        # Log in Odoo chatter
        if self.lead_id:
            self.lead_id.message_post(
                body=f"Comment posted to respond.io: {self.text}",
                message_type="comment",
                subtype_xmlid="mail.mt_note",
            )
        return {"type": "ir.actions.act_window_close"}
