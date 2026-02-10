"""Odoo XML-RPC client for communicating with Odoo 18 instances."""

import logging
import xmlrpc.client
from typing import Any

from .config import OdooConfig

logger = logging.getLogger(__name__)


class OdooClient:
    """Client for interacting with Odoo 18 via XML-RPC."""

    def __init__(self, config: OdooConfig) -> None:
        self.config = config
        self._uid: int | None = None
        self._common: xmlrpc.client.ServerProxy | None = None
        self._models: xmlrpc.client.ServerProxy | None = None

    @property
    def common(self) -> xmlrpc.client.ServerProxy:
        if self._common is None:
            self._common = xmlrpc.client.ServerProxy(
                f"{self.config.base_url}/xmlrpc/2/common",
                allow_none=True,
            )
        return self._common

    @property
    def models(self) -> xmlrpc.client.ServerProxy:
        if self._models is None:
            self._models = xmlrpc.client.ServerProxy(
                f"{self.config.base_url}/xmlrpc/2/object",
                allow_none=True,
            )
        return self._models

    @property
    def uid(self) -> int:
        if self._uid is None:
            self._uid = self.authenticate()
        return self._uid

    @property
    def _password(self) -> str:
        """Return the credential used for XML-RPC calls (API key or password)."""
        return self.config.api_key or self.config.password or ""

    def authenticate(self) -> int:
        """Authenticate with Odoo and return the user ID."""
        try:
            uid = self.common.authenticate(
                self.config.db,
                self.config.username or "",
                self._password,
                {},
            )
            if not uid:
                raise ConnectionError(
                    "Authentication failed. Check your credentials and database name."
                )
            logger.info("Authenticated with Odoo as uid=%s", uid)
            return uid
        except xmlrpc.client.Fault as e:
            raise ConnectionError(f"Odoo XML-RPC authentication error: {e.faultString}") from e
        except Exception as e:
            raise ConnectionError(f"Cannot connect to Odoo at {self.config.base_url}: {e}") from e

    def server_version(self) -> str:
        """Get the Odoo server version."""
        try:
            version_info = self.common.version()
            return version_info.get("server_version", "unknown")
        except Exception as e:
            raise ConnectionError(f"Cannot get server version: {e}") from e

    def execute_kw(
        self,
        model: str,
        method: str,
        args: list[Any] | None = None,
        kwargs: dict[str, Any] | None = None,
    ) -> Any:
        """Execute a method on an Odoo model via XML-RPC."""
        args = args or []
        kwargs = kwargs or {}
        try:
            return self.models.execute_kw(
                self.config.db,
                self.uid,
                self._password,
                model,
                method,
                args,
                kwargs,
            )
        except xmlrpc.client.Fault as e:
            raise RuntimeError(
                f"Odoo error on {model}.{method}: {e.faultString}"
            ) from e

    def search(
        self,
        model: str,
        domain: list[Any] | None = None,
        offset: int = 0,
        limit: int | None = None,
        order: str | None = None,
    ) -> list[int]:
        """Search for record IDs matching a domain."""
        domain = domain or []
        kwargs: dict[str, Any] = {"offset": offset}
        if limit is not None:
            kwargs["limit"] = limit
        if order:
            kwargs["order"] = order
        return self.execute_kw(model, "search", [domain], kwargs)

    def search_read(
        self,
        model: str,
        domain: list[Any] | None = None,
        fields: list[str] | None = None,
        offset: int = 0,
        limit: int | None = None,
        order: str | None = None,
    ) -> list[dict[str, Any]]:
        """Search and read records in a single call."""
        domain = domain or []
        kwargs: dict[str, Any] = {"offset": offset}
        if fields:
            kwargs["fields"] = fields
        if limit is not None:
            kwargs["limit"] = limit
        if order:
            kwargs["order"] = order
        return self.execute_kw(model, "search_read", [domain], kwargs)

    def read(
        self,
        model: str,
        ids: list[int],
        fields: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Read specific records by IDs."""
        kwargs: dict[str, Any] = {}
        if fields:
            kwargs["fields"] = fields
        return self.execute_kw(model, "read", [ids], kwargs)

    def create(self, model: str, values: dict[str, Any]) -> int:
        """Create a new record and return its ID."""
        return self.execute_kw(model, "create", [values])

    def write(self, model: str, ids: list[int], values: dict[str, Any]) -> bool:
        """Update existing records."""
        return self.execute_kw(model, "write", [ids, values])

    def unlink(self, model: str, ids: list[int]) -> bool:
        """Delete records."""
        return self.execute_kw(model, "unlink", [ids])

    def search_count(
        self,
        model: str,
        domain: list[Any] | None = None,
    ) -> int:
        """Count records matching a domain."""
        domain = domain or []
        return self.execute_kw(model, "search_count", [domain])

    def fields_get(
        self,
        model: str,
        attributes: list[str] | None = None,
    ) -> dict[str, Any]:
        """Get field definitions for a model."""
        attributes = attributes or ["string", "type", "required", "readonly", "help", "selection"]
        return self.execute_kw(model, "fields_get", [], {"attributes": attributes})

    def name_search(
        self,
        model: str,
        name: str = "",
        domain: list[Any] | None = None,
        limit: int = 10,
    ) -> list[list[Any]]:
        """Search records by name (display name)."""
        domain = domain or []
        return self.execute_kw(
            model,
            "name_search",
            [],
            {"name": name, "args": domain, "limit": limit},
        )
