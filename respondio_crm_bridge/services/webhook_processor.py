"""Core processor that turns incoming respond.io webhook events into Odoo records."""

import hashlib
import hmac
import json
import logging
from datetime import timedelta

from odoo import fields as odoo_fields

from . import mapping_rules

_logger = logging.getLogger(__name__)


class WebhookProcessor:
    """Stateless processor instantiated per-request.

    Parameters
    ----------
    env : odoo.api.Environment
        Odoo environment (with cursor & uid).
    account : respondio.account recordset (singleton)
    """

    def __init__(self, env, account):
        self.env = env
        self.account = account

    # ------------------------------------------------------------------
    # Signature validation
    # ------------------------------------------------------------------
    @staticmethod
    def validate_signature(secret, raw_body, signature):
        """Return True if HMAC-SHA256 of *raw_body* matches *signature*.

        If no secret is configured we skip validation (development mode).
        """
        if not secret:
            return True
        if not signature:
            return False
        expected = hmac.new(
            secret.encode("utf-8"), raw_body, hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(expected, signature)

    # ------------------------------------------------------------------
    # Idempotency
    # ------------------------------------------------------------------
    def _is_duplicate(self, event_id):
        if not event_id:
            return False
        existing = self.env["respondio.event.log"].search(
            [
                ("account_id", "=", self.account.id),
                ("event_id", "=", event_id),
                ("status", "=", "processed"),
            ],
            limit=1,
        )
        return bool(existing)

    # ------------------------------------------------------------------
    # Event log helpers
    # ------------------------------------------------------------------
    def _create_log(self, event_type, event_id, payload):
        return self.env["respondio.event.log"].create(
            {
                "account_id": self.account.id,
                "event_type": event_type,
                "event_id": event_id,
                "received_at": odoo_fields.Datetime.now(),
                "status": "received",
                "payload": json.dumps(payload, ensure_ascii=False, default=str),
            }
        )

    def _mark_processed(self, log, **extra):
        vals = {"status": "processed", "processed_at": odoo_fields.Datetime.now()}
        vals.update(extra)
        log.write(vals)

    def _mark_error(self, log, error_message):
        log.write(
            {
                "status": "error",
                "processed_at": odoo_fields.Datetime.now(),
                "error_message": str(error_message),
            }
        )

    def _mark_ignored(self, log, reason="duplicate"):
        log.write(
            {
                "status": "ignored",
                "processed_at": odoo_fields.Datetime.now(),
                "error_message": reason,
            }
        )

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------
    def process_event(self, event_type, payload, event_log=None):
        """Route an incoming event to the correct handler.

        *event_log* can be an existing ``respondio.event.log`` record (for retries).
        """
        event_id = payload.get("id") or payload.get("event_id")

        # Create log entry if not provided (retry path provides it)
        log = event_log or self._create_log(event_type, event_id, payload)

        # Idempotency check (skip for retries)
        if not event_log and self._is_duplicate(event_id):
            self._mark_ignored(log, reason="duplicate event")
            return log

        handler = self._get_handler(event_type)
        if not handler:
            self._mark_ignored(log, reason=f"unsupported event type: {event_type}")
            _logger.info("Ignoring unsupported event type: %s", event_type)
            return log

        try:
            handler(payload, log)
        except Exception as exc:
            _logger.exception("Error processing event %s (log=%s)", event_type, log.id)
            self._mark_error(log, exc)
            raise
        return log

    # ------------------------------------------------------------------
    # Handler routing
    # ------------------------------------------------------------------
    def _get_handler(self, event_type):
        """Map respond.io webhook event names to handlers.

        Official event names (10 events):
          message.created, contact.created, contact.updated,
          contact.assignee_updated, contact.tag_updated,
          contact.lifecycle_updated, conversation.opened,
          conversation.closed, comment.created
        We also accept legacy/alternative names for resilience.
        """
        mapping = {
            # ---- Official respond.io webhook events ----
            "message.created": self._handle_message_received,
            "contact.created": self._handle_contact_upsert,
            "contact.updated": self._handle_contact_upsert,
            "contact.assignee_updated": self._handle_conversation_assigned,
            "contact.tag_updated": self._handle_tag_change,
            "contact.lifecycle_updated": self._handle_contact_upsert,
            "conversation.opened": self._handle_conversation_upsert,
            "conversation.closed": self._handle_conversation_closed,
            "comment.created": self._handle_comment_created,
            # ---- Legacy / alternative names ----
            "message.received": self._handle_message_received,
            "conversation.created": self._handle_conversation_upsert,
            "conversation.updated": self._handle_conversation_upsert,
            "conversation.assigned": self._handle_conversation_assigned,
            "tag.added": self._handle_tag_change,
            "tag.removed": self._handle_tag_change,
        }
        return mapping.get(event_type)

    # ------------------------------------------------------------------
    # Contact upsert
    # ------------------------------------------------------------------
    def _upsert_contact(self, data):
        """Create or update a ``respondio.contact`` from event data."""
        Contact = self.env["respondio.contact"]
        ext_id = str(data.get("id") or data.get("contactId") or "")
        if not ext_id:
            return Contact.browse()

        existing = Contact.search(
            [("account_id", "=", self.account.id), ("respondio_id", "=", ext_id)],
            limit=1,
        )
        vals = self._contact_vals(data, ext_id)
        if existing:
            existing.write(vals)
            return existing
        vals.update(
            {
                "respondio_id": ext_id,
                "account_id": self.account.id,
            }
        )
        return Contact.create(vals)

    def _contact_vals(self, data, ext_id):
        phone_raw = data.get("phone") or data.get("phoneNumber")
        email_raw = data.get("email")
        name = (
            data.get("name")
            or data.get("displayName")
            or data.get("firstName", "")
        )
        tags_list = data.get("tags") or []
        if isinstance(tags_list, list):
            tags_str = ", ".join(str(t) for t in tags_list)
        else:
            tags_str = str(tags_list)

        channel = data.get("channel") or data.get("channelType") or ""
        vals = {
            "display_name_stored": name,
            "phone": mapping_rules.normalize_phone(phone_raw),
            "email": mapping_rules.normalize_email(email_raw),
            "tags": tags_str or False,
            "last_seen_at": odoo_fields.Datetime.now(),
            "raw_payload": json.dumps(data, ensure_ascii=False, default=str),
        }
        if channel:
            channel_lower = channel.lower()
            valid = dict(
                self.env["respondio.contact"]
                ._fields["channel"]
                .selection
            )
            if channel_lower in valid:
                vals["channel"] = channel_lower
        return vals

    # ------------------------------------------------------------------
    # Conversation upsert
    # ------------------------------------------------------------------
    def _upsert_conversation(self, data, contact=None):
        Conversation = self.env["respondio.conversation"]
        ext_id = str(data.get("id") or data.get("conversationId") or "")
        if not ext_id:
            return Conversation.browse()

        existing = Conversation.search(
            [("account_id", "=", self.account.id), ("respondio_id", "=", ext_id)],
            limit=1,
        )

        # Resolve contact if not provided
        if not contact:
            contact_data = data.get("contact") or {}
            contact_ext_id = str(
                contact_data.get("id")
                or data.get("contactId")
                or ""
            )
            if contact_ext_id:
                contact = self.env["respondio.contact"].search(
                    [
                        ("account_id", "=", self.account.id),
                        ("respondio_id", "=", contact_ext_id),
                    ],
                    limit=1,
                )

        vals = {
            "channel": data.get("channel") or data.get("channelType") or "",
            "status": (data.get("status") or "unknown").lower(),
            "last_event_at": odoo_fields.Datetime.now(),
        }
        assignee = data.get("assignee") or data.get("assignedTo") or {}
        if isinstance(assignee, dict):
            vals["assignee_name"] = assignee.get("name") or assignee.get("displayName")
            vals["assignee_external_id"] = str(assignee.get("id", "")) or False
        elif isinstance(assignee, str):
            vals["assignee_name"] = assignee

        if existing:
            if contact:
                vals["respondio_contact_id"] = contact.id
            existing.write(vals)
            return existing

        if not contact:
            return Conversation.browse()

        vals.update(
            {
                "respondio_id": ext_id,
                "account_id": self.account.id,
                "respondio_contact_id": contact.id,
            }
        )
        return Conversation.create(vals)

    # ------------------------------------------------------------------
    # Partner linking
    # ------------------------------------------------------------------
    def _ensure_partner(self, contact):
        """Link or create a partner for the contact."""
        if contact.partner_id:
            return contact.partner_id

        partner = mapping_rules.find_partner(
            self.env,
            phone=contact.phone,
            email=contact.email,
            respondio_contact=contact,
        )
        if partner:
            contact.partner_id = partner.id
            if not partner.respondio_contact_id:
                partner.respondio_contact_id = contact.id
            return partner

        if self.account.create_partner_on_new_contact:
            return mapping_rules.create_partner_from_contact(
                self.env, contact, self.account
            )
        return self.env["res.partner"].browse()

    # ------------------------------------------------------------------
    # Lead linking / creation
    # ------------------------------------------------------------------
    def _ensure_lead(self, conversation, is_new_message=False):
        """Find or create a lead for the conversation."""
        lead = mapping_rules.find_lead_for_conversation(self.env, conversation)
        if lead:
            if is_new_message:
                self._update_lead_on_message(lead, conversation)
            return lead

        # Create new lead
        lead = mapping_rules.create_lead_from_conversation(
            self.env, conversation, self.account
        )
        return lead

    def _update_lead_on_message(self, lead, conversation):
        """Update lead fields when a new message arrives."""
        lead.write(
            {
                "respondio_last_message_at": odoo_fields.Datetime.now(),
                "respondio_assignee_name": conversation.assignee_name or lead.respondio_assignee_name,
            }
        )
        # Post note in chatter
        lead.message_post(
            body=(
                f"New respond.io message received "
                f"(channel: {conversation.channel or 'N/A'}, "
                f"agent: {conversation.assignee_name or 'unassigned'})"
            ),
            message_type="comment",
            subtype_xmlid="mail.mt_note",
        )

    def _maybe_create_activity(self, lead):
        """Create a follow-up activity on the lead if configured."""
        if not self.account.auto_create_activity_on_inbound:
            return
        activity_type = self.account.activity_type_id or self.env.ref(
            "mail.mail_activity_data_todo", raise_if_not_found=False
        )
        if not activity_type:
            return
        delay = self.account.activity_delay_hours or 24
        deadline = odoo_fields.Date.context_today(lead) + timedelta(hours=delay)
        lead.activity_schedule(
            act_type_xmlid=False,
            activity_type_id=activity_type.id,
            summary=f"Follow up respond.io ({lead.respondio_channel or 'N/A'})",
            date_deadline=deadline,
            user_id=lead.user_id.id or self.env.uid,
        )

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------
    def _handle_message_received(self, payload, log):
        """New inbound message → upsert contact/conversation → lead → activity."""
        contact_data = payload.get("contact") or payload.get("data", {}).get("contact") or payload
        contact = self._upsert_contact(contact_data)
        if not contact:
            self._mark_ignored(log, "no contact id in payload")
            return

        partner = self._ensure_partner(contact)

        conv_data = payload.get("conversation") or payload.get("data", {}).get("conversation") or payload
        conversation = self._upsert_conversation(conv_data, contact=contact)
        if not conversation:
            self._mark_ignored(log, "no conversation id in payload")
            return

        conversation.write({"last_message_at": odoo_fields.Datetime.now()})

        lead = self._ensure_lead(conversation, is_new_message=True)
        self._maybe_create_activity(lead)

        self._mark_processed(
            log,
            related_lead_id=lead.id if lead else False,
            related_partner_id=partner.id if partner else False,
            related_conversation_id=conversation.id,
        )

    def _handle_contact_upsert(self, payload, log):
        """Contact created/updated in respond.io."""
        contact_data = payload.get("contact") or payload.get("data", {}).get("contact") or payload
        contact = self._upsert_contact(contact_data)
        if not contact:
            self._mark_ignored(log, "no contact id")
            return
        partner = self._ensure_partner(contact)
        self._mark_processed(
            log,
            related_partner_id=partner.id if partner else False,
        )

    def _handle_conversation_upsert(self, payload, log):
        """Conversation created/updated."""
        contact_data = payload.get("contact") or payload.get("data", {}).get("contact") or payload
        contact = self._upsert_contact(contact_data)

        conv_data = payload.get("conversation") or payload.get("data", {}).get("conversation") or payload
        conversation = self._upsert_conversation(conv_data, contact=contact)
        if not conversation:
            self._mark_ignored(log, "no conversation id")
            return
        self._mark_processed(log, related_conversation_id=conversation.id)

    def _handle_conversation_assigned(self, payload, log):
        """Agent assignment changed in respond.io."""
        conv_data = payload.get("conversation") or payload.get("data", {}).get("conversation") or payload
        contact_data = payload.get("contact") or payload.get("data", {}).get("contact") or {}
        contact = self._upsert_contact(contact_data) if contact_data.get("id") else None

        conversation = self._upsert_conversation(conv_data, contact=contact)
        if not conversation:
            self._mark_ignored(log, "no conversation id")
            return

        # Update assignee on linked lead (reflection only — no owner change)
        if conversation.lead_id and conversation.assignee_name:
            conversation.lead_id.respondio_assignee_name = conversation.assignee_name
            conversation.lead_id.message_post(
                body=f"Respond.io conversation reassigned to: {conversation.assignee_name}",
                message_type="comment",
                subtype_xmlid="mail.mt_note",
            )

        self._mark_processed(log, related_conversation_id=conversation.id)

    def _handle_conversation_closed(self, payload, log):
        """Conversation closed in respond.io."""
        conv_data = payload.get("conversation") or payload.get("data", {}).get("conversation") or payload
        contact_data = payload.get("contact") or payload.get("data", {}).get("contact") or {}
        contact = self._upsert_contact(contact_data) if contact_data.get("id") else None

        conversation = self._upsert_conversation(conv_data, contact=contact)
        if not conversation:
            self._mark_ignored(log, "no conversation id")
            return
        conversation.status = "closed"

        if conversation.lead_id:
            conversation.lead_id.message_post(
                body="Respond.io conversation was closed.",
                message_type="comment",
                subtype_xmlid="mail.mt_note",
            )
            # Create follow-up activity on close
            if self.account.auto_create_activity_on_inbound:
                activity_type = self.account.activity_type_id or self.env.ref(
                    "mail.mail_activity_data_todo", raise_if_not_found=False
                )
                if activity_type:
                    conversation.lead_id.activity_schedule(
                        act_type_xmlid=False,
                        activity_type_id=activity_type.id,
                        summary="Confirm closure — respond.io conversation closed",
                        date_deadline=odoo_fields.Date.context_today(conversation.lead_id)
                        + timedelta(days=1),
                        user_id=conversation.lead_id.user_id.id or self.env.uid,
                    )

        self._mark_processed(log, related_conversation_id=conversation.id)

    def _handle_tag_change(self, payload, log):
        """Tag added/removed on a contact (contact.tag_updated)."""
        contact_data = payload.get("contact") or payload.get("data", {}).get("contact") or payload
        contact = self._upsert_contact(contact_data)
        if not contact:
            self._mark_ignored(log, "no contact id")
            return

        # Refresh tags on linked records
        if contact.partner_id:
            contact.partner_id.respondio_tags = contact.tags
        leads = self.env["crm.lead"].search(
            [("respondio_contact_id", "=", contact.id)]
        )
        if leads:
            leads.write({"respondio_tags": contact.tags})

        self._mark_processed(
            log,
            related_partner_id=contact.partner_id.id if contact.partner_id else False,
        )

    def _handle_comment_created(self, payload, log):
        """Internal comment added on a contact (comment.created)."""
        data = payload.get("data", {}) if "data" in payload else payload
        contact_data = data.get("contact") or payload.get("contact") or {}
        contact = self._upsert_contact(contact_data) if contact_data.get("id") else None

        comment_text = data.get("text") or data.get("comment", {}).get("text") or ""

        # Post the comment as a chatter note on the most recent linked lead
        if contact and contact.partner_id:
            leads = self.env["crm.lead"].search(
                [("respondio_contact_id", "=", contact.id)],
                order="write_date desc",
                limit=1,
            )
            if leads:
                leads.message_post(
                    body=f"Comment from respond.io: {comment_text}",
                    message_type="comment",
                    subtype_xmlid="mail.mt_note",
                )

        self._mark_processed(
            log,
            related_partner_id=contact.partner_id.id if contact and contact.partner_id else False,
        )
