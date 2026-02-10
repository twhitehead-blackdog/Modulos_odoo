"""Rules for matching respond.io contacts to Odoo partners/leads."""

import logging
import re

from odoo.tools import html_escape

_logger = logging.getLogger(__name__)

# ---- Phone normalisation (best-effort E.164) ----

_PHONE_STRIP_RE = re.compile(r"[^\d+]")


def normalize_phone(raw):
    """Return a best-effort E.164 phone string, or *None*."""
    if not raw:
        return None
    cleaned = _PHONE_STRIP_RE.sub("", raw.strip())
    if not cleaned:
        return None
    if not cleaned.startswith("+"):
        cleaned = "+" + cleaned
    return cleaned


def normalize_email(raw):
    if not raw:
        return None
    return raw.strip().lower() or None


# ------------------------------------------------------------------
# Partner matching
# ------------------------------------------------------------------

def find_partner(env, phone=None, email=None, respondio_contact=None):
    """Try to find an existing ``res.partner`` using the best available key.

    Order of precedence:
    1. ``respondio_contact_id`` (direct link already set)
    2. Phone (normalised)
    3. Email (lowercase)

    Returns a ``res.partner`` recordset (empty if no match).
    """
    Partner = env["res.partner"]

    # 1. Already linked via respondio_contact_id
    if respondio_contact:
        linked = Partner.search(
            [("respondio_contact_id", "=", respondio_contact.id)], limit=1
        )
        if linked:
            return linked

    # 2. Phone match
    norm_phone = normalize_phone(phone)
    if norm_phone:
        match = Partner.search(
            ["|", ("phone", "=", norm_phone), ("mobile", "=", norm_phone)],
            limit=1,
        )
        if match:
            return match

    # 3. Email match
    norm_email = normalize_email(email)
    if norm_email:
        match = Partner.search([("email", "=ilike", norm_email)], limit=1)
        if match:
            return match

    return Partner.browse()


# ------------------------------------------------------------------
# Lead matching / creation
# ------------------------------------------------------------------

def find_lead_for_conversation(env, conversation):
    """Return the ``crm.lead`` linked to *conversation*, or empty recordset."""
    if conversation.lead_id:
        return conversation.lead_id
    Lead = env["crm.lead"]
    lead = Lead.search(
        [("respondio_conversation_id", "=", conversation.id)], limit=1
    )
    return lead


def create_lead_from_conversation(env, conversation, account):
    """Create a new ``crm.lead`` from a respond.io conversation + account defaults."""
    contact = conversation.respondio_contact_id
    partner = contact.partner_id

    name_parts = [contact.display_name_stored or "Unknown"]
    if conversation.channel:
        name_parts.append(conversation.channel)
    lead_name = " - ".join(name_parts)

    vals = {
        "name": lead_name,
        "respondio_conversation_id": conversation.id,
        "respondio_contact_id": contact.id,
        "respondio_channel": conversation.channel,
        "respondio_last_message_at": conversation.last_message_at,
        "respondio_tags": contact.tags,
        "respondio_assignee_name": conversation.assignee_name,
        "type": "opportunity",
    }

    if partner:
        vals["partner_id"] = partner.id
        if partner.email:
            vals["email_from"] = partner.email
        if partner.phone or partner.mobile:
            vals["phone"] = partner.phone or partner.mobile

    if account.default_team_id:
        vals["team_id"] = account.default_team_id.id
    if account.default_user_id:
        vals["user_id"] = account.default_user_id.id
    if account.default_lead_stage_id:
        vals["stage_id"] = account.default_lead_stage_id.id

    lead = env["crm.lead"].create(vals)
    conversation.lead_id = lead.id
    _logger.info(
        "Created lead %s (id=%d) for conversation %s",
        lead.name,
        lead.id,
        conversation.respondio_id,
    )
    return lead


def create_partner_from_contact(env, contact, account):
    """Create a minimal ``res.partner`` from a respond.io contact."""
    vals = {
        "name": contact.display_name_stored or f"Prospect ({contact.respondio_id})",
        "respondio_contact_id": contact.id,
        "respondio_tags": contact.tags,
    }
    phone = normalize_phone(contact.phone)
    if phone:
        vals["mobile"] = phone
    email = normalize_email(contact.email)
    if email:
        vals["email"] = email

    partner = env["res.partner"].create(vals)
    contact.partner_id = partner.id
    _logger.info(
        "Created partner %s (id=%d) for respondio contact %s",
        partner.name,
        partner.id,
        contact.respondio_id,
    )
    return partner
