import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class CrmLead(models.Model):
    _inherit = "crm.lead"

    respondio_conversation_id = fields.Many2one(
        "respondio.conversation",
        string="Respond.io Conversation",
        index=True,
    )
    respondio_contact_id = fields.Many2one(
        "respondio.contact",
        string="Respond.io Contact",
        index=True,
    )
    respondio_channel = fields.Char(string="Respond.io Channel")
    respondio_last_message_at = fields.Datetime(string="Last Message (respond.io)")
    respondio_url = fields.Char(
        string="Respond.io URL",
        compute="_compute_respondio_url",
        store=True,
    )
    respondio_tags = fields.Char(string="Respond.io Tags")
    respondio_assignee_name = fields.Char(string="Respond.io Agent")

    @api.depends("respondio_conversation_id.respondio_url")
    def _compute_respondio_url(self):
        for rec in self:
            if rec.respondio_conversation_id:
                rec.respondio_url = rec.respondio_conversation_id.respondio_url
            else:
                rec.respondio_url = False

    # ---- Actions ----
    def action_open_in_respondio(self):
        """Open the linked conversation in respond.io (new browser tab)."""
        self.ensure_one()
        if not self.respondio_url:
            return
        return {
            "type": "ir.actions.act_url",
            "url": self.respondio_url,
            "target": "new",
        }

    def action_respondio_send_message(self):
        """Open wizard to send an outbound message via respond.io."""
        self.ensure_one()
        if not self.respondio_contact_id:
            return
        return {
            "type": "ir.actions.act_window",
            "name": "Send Message via Respond.io",
            "res_model": "respondio.send.message.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_lead_id": self.id,
                "default_respondio_contact_id": self.respondio_contact_id.id,
                "default_account_id": self.respondio_contact_id.account_id.id,
            },
        }

    def action_create_followup_activity(self):
        """Create a follow-up activity linked to respond.io conversation."""
        self.ensure_one()
        account = (
            self.respondio_conversation_id.account_id
            if self.respondio_conversation_id
            else self.env["respondio.account"].search(
                [("company_id", "=", self.company_id.id)], limit=1
            )
        )
        activity_type = (
            account.activity_type_id
            if account and account.activity_type_id
            else self.env.ref("mail.mail_activity_data_todo", raise_if_not_found=False)
        )
        delay_hours = account.activity_delay_hours if account else 24
        from datetime import timedelta

        self.activity_schedule(
            act_type_xmlid=False,
            activity_type_id=activity_type.id if activity_type else False,
            summary=f"Follow up respond.io conversation ({self.respondio_channel or 'N/A'})",
            date_deadline=fields.Date.context_today(self)
            + timedelta(hours=delay_hours),
            user_id=self.user_id.id or self.env.uid,
        )
