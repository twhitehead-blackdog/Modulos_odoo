"""Client wrapper for the respond.io REST API (v2).

Base URL: https://api.respond.io/v2
Auth: Bearer token
Contact identifiers: ``id:123``, ``email:user@example.com``, ``phone:+60121233112``
Pagination: cursor-based with ``limit`` (1-100) and ``cursorId``
Rate limiting: 429 with ``retry-after``, ``x-ratelimit-limit``, ``x-ratelimit-remaining``

Full endpoint reference — 28 endpoints across 5 domains:
  Contact (11), Messaging (3), Conversation (2), Comment (1), Space (11)
"""

import logging
import time

import requests

_logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 30  # seconds (respond.io default)
MAX_RETRIES = 3
RETRY_BACKOFF = 2  # exponential base


def _build_identifier(respondio_id=None, email=None, phone=None):
    """Build a respond.io contact identifier string.

    The API accepts ``id:<int>``, ``email:<str>``, or ``phone:<E.164>``.
    Priority: id > email > phone.
    """
    if respondio_id:
        rid = str(respondio_id)
        if rid.startswith(("id:", "email:", "phone:")):
            return rid
        return f"id:{rid}"
    if email:
        return f"email:{email}"
    if phone:
        return f"phone:{phone}"
    raise ValueError("At least one of respondio_id, email, or phone is required")


class RespondioAPI:
    """Thin wrapper around respond.io HTTP API v2.

    Receives a ``respondio.account`` recordset (singleton) for credentials.
    All public methods return parsed JSON or raise on failure.
    """

    def __init__(self, account):
        self.base_url = (account.api_base_url or "").rstrip("/")
        self.token = account.api_token or ""
        self.account_id = account.id

    # ------------------------------------------------------------------
    # Low-level HTTP
    # ------------------------------------------------------------------
    def _request(self, method, endpoint, payload=None, params=None, timeout=DEFAULT_TIMEOUT):
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        last_exc = None
        for attempt in range(MAX_RETRIES):
            try:
                resp = requests.request(
                    method, url, headers=headers, json=payload,
                    params=params, timeout=timeout,
                )
                # 429 — rate limited; respect Retry-After header
                if resp.status_code == 429:
                    retry_after = float(
                        resp.headers.get("retry-after", RETRY_BACKOFF ** (attempt + 1))
                    )
                    _logger.warning(
                        "respond.io API rate-limited (%s %s), retry in %.1fs "
                        "(limit=%s, remaining=%s)",
                        method, endpoint, retry_after,
                        resp.headers.get("x-ratelimit-limit", "?"),
                        resp.headers.get("x-ratelimit-remaining", "?"),
                    )
                    if attempt < MAX_RETRIES - 1:
                        time.sleep(retry_after)
                        continue
                    resp.raise_for_status()

                resp.raise_for_status()
                return resp.json() if resp.content else {}

            except requests.RequestException as exc:
                last_exc = exc
                _logger.warning(
                    "respond.io API %s %s attempt %d failed: %s",
                    method, endpoint, attempt + 1, exc,
                )
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_BACKOFF ** (attempt + 1))

        raise last_exc  # type: ignore[misc]

    # ==================================================================
    # CONTACT API  (11 endpoints)
    # ==================================================================

    def test_connection(self):
        """Verify credentials with a lightweight list call."""
        return self._request("POST", "/contact/list", payload={}, params={"limit": 1})

    def get_contact(self, respondio_id=None, email=None, phone=None):
        """``GET /contact/{identifier}``"""
        ident = _build_identifier(respondio_id, email, phone)
        return self._request("GET", f"/contact/{ident}")

    def create_contact(self, identifier_email=None, identifier_phone=None, fields=None):
        """``POST /contact/{identifier}`` — identifier must be email: or phone:.

        *fields*: dict with firstName, lastName, phone, email, language,
        countryCode, custom_fields, etc.
        """
        if identifier_email:
            ident = f"email:{identifier_email}"
        elif identifier_phone:
            ident = f"phone:{identifier_phone}"
        else:
            raise ValueError("create_contact requires email or phone identifier")
        return self._request("POST", f"/contact/{ident}", payload=fields or {})

    def update_contact(self, respondio_id, data):
        """``PUT /contact/{identifier}``"""
        ident = _build_identifier(respondio_id)
        return self._request("PUT", f"/contact/{ident}", payload=data)

    def delete_contact(self, respondio_id):
        """``DELETE /contact/{identifier}``"""
        ident = _build_identifier(respondio_id)
        return self._request("DELETE", f"/contact/{ident}")

    def create_or_update_contact(self, respondio_id=None, email=None, phone=None, fields=None):
        """``POST /contact/create_or_update/{identifier}``"""
        ident = _build_identifier(respondio_id, email, phone)
        return self._request("POST", f"/contact/create_or_update/{ident}", payload=fields or {})

    def merge_contacts(self, contact_ids, override_fields=None):
        """``POST /contact/merge``

        *contact_ids*: list of two integer IDs.
        *override_fields*: optional dict (firstName, lastName, etc.).
        """
        body = {"contactIds": contact_ids}
        if override_fields:
            body.update(override_fields)
        return self._request("POST", "/contact/merge", payload=body)

    def list_contacts(self, limit=10, cursor_id=None, search="", filter_rules=None):
        """``POST /contact/list``

        *filter_rules*: dict with ``$and`` key containing filter objects, e.g.
        ``{"$and": [{"category":"contactField","field":"assigneeUserId",
        "operator":"isEqualTo","value":"123"}]}``
        """
        body = {"search": search}
        if filter_rules:
            body["filter"] = filter_rules
        params = {"limit": limit}
        if cursor_id:
            params["cursorId"] = cursor_id
        return self._request("POST", "/contact/list", payload=body, params=params)

    def add_tags(self, respondio_id, tags):
        """``POST /contact/{identifier}/tag`` — *tags*: list of strings (1-10, max 255 chars each)."""
        ident = _build_identifier(respondio_id)
        return self._request("POST", f"/contact/{ident}/tag", payload=tags)

    def remove_tags(self, respondio_id, tags):
        """``DELETE /contact/{identifier}/tag``"""
        ident = _build_identifier(respondio_id)
        return self._request("DELETE", f"/contact/{ident}/tag", payload=tags)

    def list_contact_channels(self, respondio_id, limit=10, cursor_id=None):
        """``GET /contact/{identifier}/channels``"""
        ident = _build_identifier(respondio_id)
        params = {"limit": limit}
        if cursor_id:
            params["cursorId"] = cursor_id
        return self._request("GET", f"/contact/{ident}/channels", params=params)

    def update_contact_lifecycle(self, respondio_id, lifecycle_name=None):
        """``POST /contact/{identifier}/lifecycle/update``

        Pass *lifecycle_name*=None to remove the lifecycle.
        """
        ident = _build_identifier(respondio_id)
        return self._request(
            "POST", f"/contact/{ident}/lifecycle/update",
            payload={"name": lifecycle_name},
        )

    # ==================================================================
    # MESSAGING API  (3 endpoints)
    # ==================================================================

    def send_message(self, respondio_id, message_obj, channel_id=None):
        """``POST /contact/{identifier}/message``

        *message_obj*: dict matching one of the respond.io message types:
          - ``{"type": "text", "text": "Hello"}``
          - ``{"type": "attachment", "attachment": {"type": "image", "url": "..."}}``
          - ``{"type": "quick_reply", "title": "Choose:", "replies": ["A","B"]}``
          - ``{"type": "email", "text": "...", "subject": "..."}``
          - ``{"type": "whatsapp_template", "template": {...}}``
        *channel_id*: optional int; defaults to last-interacted channel.
        """
        ident = _build_identifier(respondio_id)
        body = {"message": message_obj}
        if channel_id:
            body["channelId"] = channel_id
        return self._request("POST", f"/contact/{ident}/message", payload=body)

    def send_text_message(self, respondio_id, text, channel_id=None):
        """Convenience: send a plain text message."""
        return self.send_message(
            respondio_id,
            {"type": "text", "text": text},
            channel_id=channel_id,
        )

    def get_message(self, respondio_id, message_id):
        """``GET /contact/{identifier}/message/{messageId}``"""
        ident = _build_identifier(respondio_id)
        return self._request("GET", f"/contact/{ident}/message/{message_id}")

    def list_messages(self, respondio_id, limit=10, cursor_id=None):
        """``GET /contact/{identifier}/message/list``"""
        ident = _build_identifier(respondio_id)
        params = {"limit": limit}
        if cursor_id:
            params["cursorId"] = cursor_id
        return self._request("GET", f"/contact/{ident}/message/list", params=params)

    # ==================================================================
    # CONVERSATION API  (2 endpoints)
    # ==================================================================

    def assign_conversation(self, respondio_id, assignee):
        """``POST /contact/{identifier}/conversation/assignee``

        *assignee*: user ID (int), user email (str), or None to unassign.
        """
        ident = _build_identifier(respondio_id)
        return self._request(
            "POST", f"/contact/{ident}/conversation/assignee",
            payload={"assignee": assignee},
        )

    def set_conversation_status(self, respondio_id, status, category=None, summary=None):
        """``POST /contact/{identifier}/conversation/status``

        *status*: ``"open"`` or ``"close"``.
        *category*/*summary*: only used when closing.
        """
        ident = _build_identifier(respondio_id)
        body = {"status": status}
        if status == "close":
            if category:
                body["category"] = category
            if summary:
                body["summary"] = summary
        return self._request(
            "POST", f"/contact/{ident}/conversation/status", payload=body,
        )

    # ==================================================================
    # COMMENT API  (1 endpoint)
    # ==================================================================

    def create_comment(self, respondio_id=None, email=None, phone=None, text=""):
        """``POST /contact/{identifier}/comment``

        Max 1000 characters. Supports ``{{@user.ID}}`` mentions and
        ``{{$contact.name}}`` dynamic variables.
        """
        ident = _build_identifier(respondio_id, email, phone)
        return self._request(
            "POST", f"/contact/{ident}/comment",
            payload={"text": text[:1000]},
        )

    # ==================================================================
    # SPACE / WORKSPACE API  (11 endpoints)
    # ==================================================================

    def list_users(self, limit=10, cursor_id=None):
        """``GET /space/user``"""
        params = {"limit": limit}
        if cursor_id:
            params["cursorId"] = cursor_id
        return self._request("GET", "/space/user", params=params)

    def get_user(self, user_id):
        """``GET /space/user/{id}``"""
        return self._request("GET", f"/space/user/{user_id}")

    def create_custom_field(self, name, slug, data_type, description="", allowed_values=None):
        """``POST /space/custom_field``

        *data_type*: text, list, checkbox, email, number, url, date, time.
        *allowed_values*: only for ``list`` type.
        """
        body = {
            "name": name,
            "slug": slug,
            "description": description,
            "dataType": data_type,
        }
        if allowed_values is not None:
            body["allowedValues"] = allowed_values
        return self._request("POST", "/space/custom_field", payload=body)

    def list_custom_fields(self, limit=10, cursor_id=None):
        """``GET /space/custom_field``"""
        params = {"limit": limit}
        if cursor_id:
            params["cursorId"] = cursor_id
        return self._request("GET", "/space/custom_field", params=params)

    def get_custom_field(self, field_id):
        """``GET /space/custom_field/{id}``"""
        return self._request("GET", f"/space/custom_field/{field_id}")

    def list_closing_notes(self, limit=10, cursor_id=None):
        """``GET /space/closing_notes``"""
        params = {"limit": limit}
        if cursor_id:
            params["cursorId"] = cursor_id
        return self._request("GET", "/space/closing_notes", params=params)

    def list_channels(self, limit=10, cursor_id=None):
        """``GET /space/channel``"""
        params = {"limit": limit}
        if cursor_id:
            params["cursorId"] = cursor_id
        return self._request("GET", "/space/channel", params=params)

    def list_templates(self, channel_id, limit=10, cursor_id=None):
        """``GET /space/channel/{channelId}/template``"""
        params = {"limit": limit}
        if cursor_id:
            params["cursorId"] = cursor_id
        return self._request("GET", f"/space/channel/{channel_id}/template", params=params)

    def create_tag(self, name, description="", color_code=None, emoji=None):
        """``POST /space/tag``"""
        body = {"name": name, "description": description}
        if color_code:
            body["colorCode"] = color_code
        if emoji:
            body["emoji"] = emoji
        return self._request("POST", "/space/tag", payload=body)

    def update_tag(self, current_name, name=None, description=None, color_code=None, emoji=None):
        """``PUT /space/tag``"""
        body = {"currentName": current_name}
        if name:
            body["name"] = name
        if description is not None:
            body["description"] = description
        if color_code:
            body["colorCode"] = color_code
        if emoji:
            body["emoji"] = emoji
        return self._request("PUT", "/space/tag", payload=body)

    def delete_tag(self, name):
        """``DELETE /space/tag``"""
        return self._request("DELETE", "/space/tag", payload={"name": name})
