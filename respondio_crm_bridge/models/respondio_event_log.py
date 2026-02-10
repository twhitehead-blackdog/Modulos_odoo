import json
import logging
from datetime import timedelta

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class RespondioEventLog(models.Model):
    _name = "respondio.event.log"
    _description = "Respond.io Event Log"
    _order = "received_at desc, id desc"
    _rec_name = "event_type"

    account_id = fields.Many2one(
        "respondio.account",
        ondelete="set null",
        index=True,
    )
    event_type = fields.Char(index=True)
    event_id = fields.Char(
        string="Event ID",
        index=True,
        help="Unique event identifier from respond.io (used for idempotency)",
    )
    received_at = fields.Datetime(default=fields.Datetime.now)
    processed_at = fields.Datetime()
    status = fields.Selection(
        [
            ("received", "Received"),
            ("processed", "Processed"),
            ("ignored", "Ignored"),
            ("error", "Error"),
        ],
        default="received",
        index=True,
    )
    error_message = fields.Text()
    payload = fields.Text(
        help="Full JSON payload from the webhook",
        groups="respondio_crm_bridge.group_respondio_admin",
    )
    retry_count = fields.Integer(default=0)
    max_retries = fields.Integer(default=3)
    related_lead_id = fields.Many2one("crm.lead", string="Lead")
    related_partner_id = fields.Many2one("res.partner", string="Partner")
    related_conversation_id = fields.Many2one(
        "respondio.conversation", string="Conversation"
    )

    def action_retry(self):
        """Manually retry processing a failed event."""
        self.ensure_one()
        if self.status != "error":
            return
        from ..services.webhook_processor import WebhookProcessor

        processor = WebhookProcessor(self.env, self.account_id)
        try:
            payload = json.loads(self.payload) if self.payload else {}
            processor.process_event(self.event_type, payload, event_log=self)
        except Exception as exc:
            _logger.exception("Manual retry failed for event %s", self.id)
            self.write(
                {
                    "status": "error",
                    "error_message": str(exc),
                    "retry_count": self.retry_count + 1,
                }
            )

    # ------------------------------------------------------------------
    # Cron methods
    # ------------------------------------------------------------------
    @api.model
    def _cron_retry_failed(self):
        """Retry events with status=error that haven't exceeded max retries."""
        failed = self.search(
            [
                ("status", "=", "error"),
                ("retry_count", "<", 3),
                ("account_id", "!=", False),
            ],
            limit=100,
        )
        from ..services.webhook_processor import WebhookProcessor

        for log in failed:
            try:
                processor = WebhookProcessor(self.env, log.account_id)
                payload = json.loads(log.payload) if log.payload else {}
                processor.process_event(log.event_type, payload, event_log=log)
            except Exception as exc:
                _logger.warning(
                    "Cron retry failed for event log %s: %s", log.id, exc
                )
                log.write(
                    {
                        "retry_count": log.retry_count + 1,
                        "error_message": str(exc),
                    }
                )

    @api.model
    def _cron_clean_old_logs(self):
        """Delete processed/ignored event logs older than 90 days."""
        cutoff = fields.Datetime.now() - timedelta(days=90)
        old_logs = self.search(
            [
                ("status", "in", ["processed", "ignored"]),
                ("received_at", "<", cutoff),
            ],
            limit=5000,
        )
        if old_logs:
            _logger.info("Cleaning %d old respond.io event logs", len(old_logs))
            old_logs.unlink()
