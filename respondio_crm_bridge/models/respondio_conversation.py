import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class RespondioConversation(models.Model):
    _name = "respondio.conversation"
    _description = "Respond.io Conversation"
    _order = "last_message_at desc, id desc"
    _rec_name = "display_name"

    respondio_id = fields.Char(
        string="Respond.io ID",
        required=True,
        index=True,
    )
    account_id = fields.Many2one(
        "respondio.account",
        required=True,
        ondelete="cascade",
        index=True,
    )
    respondio_contact_id = fields.Many2one(
        "respondio.contact",
        required=True,
        ondelete="cascade",
        index=True,
    )
    partner_id = fields.Many2one(
        "res.partner",
        related="respondio_contact_id.partner_id",
        store=True,
        string="Odoo Contact",
    )
    lead_id = fields.Many2one(
        "crm.lead",
        string="Opportunity",
        index=True,
    )
    channel = fields.Char(string="Channel")
    status = fields.Selection(
        [
            ("open", "Open"),
            ("pending", "Pending"),
            ("closed", "Closed"),
            ("unknown", "Unknown"),
        ],
        default="unknown",
        index=True,
    )
    assignee_name = fields.Char(string="Assigned Agent")
    assignee_external_id = fields.Char(string="Agent External ID")
    last_message_at = fields.Datetime(string="Last Message")
    last_event_at = fields.Datetime(string="Last Event")
    respondio_url = fields.Char(
        string="Respond.io URL",
        compute="_compute_respondio_url",
        store=True,
    )
    display_name = fields.Char(compute="_compute_display_name", store=True)

    _sql_constraints = [
        (
            "unique_respondio_conversation",
            "UNIQUE(account_id, respondio_id)",
            "A respond.io conversation must be unique per account.",
        ),
    ]

    @api.depends("respondio_contact_id.display_name_stored", "respondio_id", "channel")
    def _compute_display_name(self):
        for rec in self:
            contact_name = (
                rec.respondio_contact_id.display_name_stored or rec.respondio_id
            )
            suffix = f" ({rec.channel})" if rec.channel else ""
            rec.display_name = f"{contact_name}{suffix}"

    @api.depends("account_id.respondio_space_url", "respondio_id")
    def _compute_respondio_url(self):
        for rec in self:
            base = rec.account_id.respondio_space_url
            if base and rec.respondio_id:
                base = base.rstrip("/")
                rec.respondio_url = f"{base}/inbox/{rec.respondio_id}"
            else:
                rec.respondio_url = False

    def action_open_in_respondio(self):
        self.ensure_one()
        if not self.respondio_url:
            return
        return {
            "type": "ir.actions.act_url",
            "url": self.respondio_url,
            "target": "new",
        }
