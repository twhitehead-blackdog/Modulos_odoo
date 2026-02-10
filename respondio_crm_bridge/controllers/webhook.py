"""HTTP controller that receives respond.io webhook events.

Webhook payload format: ``{"event": "message.created", "data": {...}}``
Signature header: ``x-respond-signature`` (HMAC-SHA256)
Must return HTTP 200 within 5 seconds.
Auto-disabled after 30+ errors in 30 minutes.
"""

import json
import logging

from odoo import http
from odoo.http import request, Response

from ..services.webhook_processor import WebhookProcessor

_logger = logging.getLogger(__name__)


class RespondioWebhookController(http.Controller):

    @http.route(
        "/respondio/webhook/<int:account_id>",
        type="json",
        auth="none",
        methods=["POST"],
        csrf=False,
    )
    def receive_webhook(self, account_id, **kwargs):
        """Main webhook endpoint (JSON content-type).

        URL: ``POST /respondio/webhook/<account_id>``
        """
        env = request.env(su=True)

        account = env["respondio.account"].browse(account_id).exists()
        if not account or not account.active:
            _logger.warning("Webhook for unknown/inactive account %s", account_id)
            return {"status": "error", "message": "unknown account"}

        raw_body = request.httprequest.get_data()
        signature = (
            request.httprequest.headers.get("x-respond-signature")
            or request.httprequest.headers.get("X-Signature", "")
        )

        if not WebhookProcessor.validate_signature(
            account.webhook_secret, raw_body, signature
        ):
            _logger.warning("Invalid webhook signature for account %s", account_id)
            return {"status": "error", "message": "invalid signature"}

        try:
            payload = json.loads(raw_body) if raw_body else {}
        except (json.JSONDecodeError, ValueError):
            _logger.error("Invalid JSON in webhook body for account %s", account_id)
            return {"status": "error", "message": "invalid JSON"}

        event_type = (
            payload.get("event")
            or payload.get("type")
            or payload.get("event_type")
            or "unknown"
        )

        _logger.info(
            "Received respond.io webhook: account=%s type=%s",
            account_id,
            event_type,
        )

        processor = WebhookProcessor(env, account)
        try:
            log = processor.process_event(event_type, payload)
            return {
                "status": "ok",
                "log_id": log.id,
                "event_status": log.status,
            }
        except Exception:
            _logger.exception(
                "Webhook processing failed: account=%s type=%s",
                account_id,
                event_type,
            )
            return {"status": "error", "message": "processing failed"}

    # ------------------------------------------------------------------
    # Fallback HTTP endpoint for non-JSON content-type
    # ------------------------------------------------------------------
    @http.route(
        "/respondio/webhook/http/<int:account_id>",
        type="http",
        auth="none",
        methods=["POST"],
        csrf=False,
    )
    def receive_webhook_http(self, account_id, **kwargs):
        """Fallback HTTP endpoint that accepts any content-type."""
        env = request.env(su=True)

        account = env["respondio.account"].browse(account_id).exists()
        if not account or not account.active:
            return Response("unknown account", status=404)

        raw_body = request.httprequest.get_data()
        signature = (
            request.httprequest.headers.get("x-respond-signature")
            or request.httprequest.headers.get("X-Signature", "")
        )

        if not WebhookProcessor.validate_signature(
            account.webhook_secret, raw_body, signature
        ):
            return Response("invalid signature", status=403)

        try:
            payload = json.loads(raw_body) if raw_body else {}
        except (json.JSONDecodeError, ValueError):
            return Response("invalid JSON", status=400)

        event_type = (
            payload.get("event")
            or payload.get("type")
            or payload.get("event_type")
            or "unknown"
        )

        processor = WebhookProcessor(env, account)
        try:
            processor.process_event(event_type, payload)
            return Response("ok", status=200)
        except Exception:
            _logger.exception(
                "Webhook processing failed: account=%s type=%s",
                account_id,
                event_type,
            )
            return Response("processing failed", status=500)
