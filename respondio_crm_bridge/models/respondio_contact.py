import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class RespondioContact(models.Model):
    _name = "respondio.contact"
    _description = "Respond.io Contact (shadow record)"
    _order = "last_seen_at desc, id desc"
    _rec_name = "display_name_stored"

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
    partner_id = fields.Many2one(
        "res.partner",
        string="Odoo Contact",
        index=True,
    )
    display_name_stored = fields.Char(string="Name")
    phone = fields.Char(index=True)
    email = fields.Char(index=True)
    channel = fields.Selection(
        [
            ("facebook", "Facebook Messenger"),
            ("instagram", "Instagram"),
            ("line", "LINE"),
            ("telegram", "Telegram"),
            ("viber", "Viber"),
            ("twitter", "Twitter"),
            ("wechat", "WeChat"),
            ("custom_channel", "Custom Channel"),
            ("gmail", "Gmail"),
            ("other_email", "Other Email"),
            ("twilio", "Twilio"),
            ("message_bird", "MessageBird"),
            ("nexmo", "Nexmo"),
            ("360dialog_whatsapp", "360dialog WhatsApp"),
            ("twilio_whatsapp", "Twilio WhatsApp"),
            ("message_bird_whatsapp", "MessageBird WhatsApp"),
            ("whatsapp", "WhatsApp"),
            ("nexmo_whatsapp", "Nexmo WhatsApp"),
            ("whatsapp_cloud", "WhatsApp Cloud"),
            ("sms", "SMS"),
            ("webchat", "Web Chat"),
            ("other", "Other"),
        ],
        string="Primary Channel",
    )
    tags = fields.Char(help="Comma-separated tags from respond.io")
    last_seen_at = fields.Datetime(string="Last Seen")
    raw_payload = fields.Text(
        string="Raw Payload",
        groups="respondio_crm_bridge.group_respondio_admin",
    )

    _sql_constraints = [
        (
            "unique_respondio_contact",
            "UNIQUE(account_id, respondio_id)",
            "A respond.io contact must be unique per account.",
        ),
    ]

    def name_get(self):
        return [
            (r.id, r.display_name_stored or f"Contact #{r.respondio_id}")
            for r in self
        ]
