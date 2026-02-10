"""HTTP controller that receives respond.io webhook events."""

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
        """Main webhook endpoint.

        URL: ``POST /respondio/webhook/<account_id>``
        Expects JSON body with at least ``event`` (type string) and payload data.
        """
        env = request.env(su=True)

        # Resolve account
        account = env["respondio.account"].browse(account_id).exists()
        if not account or not account.active:
            _logger.warning("Webhook for unknown/inactive account %s", account_id)
            return {"status": "error", "message": "unknown account"}

        # Read raw body for signature validation
        raw_body = request.httprequest.get_data()
        signature = request.httprequest.headers.get("X-Signature", "")

        if not WebhookProcessor.validate_signature(
            account.webhook_secret, raw_body, signature
        ):
            _logger.warning("Invalid webhook signature for account %s", account_id)
            return {"status": "error", "message": "invalid signature"}

        # Parse payload
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

        # Process
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
    # Alternative HTTP endpoint (type="http") for providers that don't
    # send application/json content-type.
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
        signature = request.httprequest.headers.get("X-Signature", "")

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
