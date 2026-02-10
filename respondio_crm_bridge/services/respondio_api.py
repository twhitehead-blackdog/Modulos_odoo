"""Client wrapper for the respond.io REST API."""

import json
import logging
import time

import requests

_logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 15  # seconds
MAX_RETRIES = 3
RETRY_BACKOFF = 2  # exponential base


class RespondioAPI:
    """Thin wrapper around respond.io HTTP API.

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

    def get_contact(self, respondio_contact_id):
        return self._request("GET", f"/contact/{respondio_contact_id}")

    def update_contact(self, respondio_contact_id, data):
        return self._request("PUT", f"/contact/{respondio_contact_id}", payload=data)

    def tag_contact(self, respondio_contact_id, tags):
        """Add tags to a contact. *tags* is a list of tag name strings."""
        return self._request(
            "POST",
            f"/contact/{respondio_contact_id}/tag",
            payload={"tags": tags},
        )

    def send_message(self, respondio_contact_id, channel, message):
        """Send an outbound text message via respond.io."""
        return self._request(
            "POST",
            f"/contact/{respondio_contact_id}/message",
            payload={
                "channelId": channel,
                "message": {"type": "text", "text": message},
            },
        )

    def get_conversation(self, respondio_conversation_id):
        return self._request("GET", f"/conversation/{respondio_conversation_id}")
