"""Client wrapper for the respond.io REST API (v2).

Reference: https://api.respond.io/v2
Auth: Bearer token
Contact identifiers accept: ``id:123``, ``email:user@example.com``, ``phone:+60121233112``
"""

import logging
import time

import requests

_logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 15  # seconds
MAX_RETRIES = 3
RETRY_BACKOFF = 2  # exponential base


def _build_identifier(respondio_id=None, email=None, phone=None):
    """Build a respond.io contact identifier string.

    The API accepts ``id:<int>``, ``email:<str>``, or ``phone:<E.164>``.
    We try them in order of specificity.
    """
    if respondio_id:
        rid = str(respondio_id)
        # If already prefixed, return as-is
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
    # Low-level request
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
                    method,
                    url,
                    headers=headers,
                    json=payload,
                    params=params,
                    timeout=timeout,
                )
                # Handle rate limiting (429) with Retry-After header
                if resp.status_code == 429:
                    retry_after = float(resp.headers.get("Retry-After", RETRY_BACKOFF ** (attempt + 1)))
                    _logger.warning(
                        "respond.io API rate limited (%s %s), retrying in %.1fs "
                        "(limit=%s, remaining=%s)",
                        method,
                        endpoint,
                        retry_after,
                        resp.headers.get("X-RateLimit-Limit", "?"),
                        resp.headers.get("X-RateLimit-Remaining", "?"),
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
                    method,
                    endpoint,
                    attempt + 1,
                    exc,
                )
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_BACKOFF ** (attempt + 1))
        raise last_exc  # type: ignore[misc]

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------
    def test_connection(self):
        """Simple GET to verify credentials."""
        return self._request("GET", "/contact")

    def get_contact(self, respondio_id=None, email=None, phone=None):
        """Get a contact by identifier."""
        identifier = _build_identifier(respondio_id, email, phone)
        return self._request("GET", f"/contact/{identifier}")

    def update_contact(self, respondio_id, data):
        identifier = _build_identifier(respondio_id)
        return self._request("PUT", f"/contact/{identifier}", payload=data)

    def tag_contact(self, respondio_id, tags):
        """Add tags to a contact. *tags* is a list of tag name strings."""
        identifier = _build_identifier(respondio_id)
        return self._request(
            "POST",
            f"/contact/{identifier}/tag",
            payload={"tags": tags},
        )

    def send_message(self, respondio_id, channel, message):
        """Send an outbound text message via respond.io."""
        identifier = _build_identifier(respondio_id)
        return self._request(
            "POST",
            f"/contact/{identifier}/message",
            payload={
                "channelId": channel,
                "message": {"type": "text", "text": message},
            },
        )

    def create_comment(self, respondio_id=None, email=None, phone=None, text=""):
        """Add an internal comment to a contact in respond.io.

        ``POST /contact/{identifier}/comment``

        *text* supports mentions (``{{@user.ID}}``) and dynamic variables
        (``{{$contact.name}}``).  Max 1000 characters.
        """
        identifier = _build_identifier(respondio_id, email, phone)
        return self._request(
            "POST",
            f"/contact/{identifier}/comment",
            payload={"text": text[:1000]},
        )

    def get_conversation(self, respondio_conversation_id):
        return self._request("GET", f"/conversation/{respondio_conversation_id}")
