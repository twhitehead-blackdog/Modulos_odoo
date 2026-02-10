"""Configuration management for Odoo MCP Server."""

import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass
class OdooConfig:
    """Odoo connection configuration."""

    url: str
    db: str
    username: str | None = None
    password: str | None = None
    api_key: str | None = None

    @property
    def base_url(self) -> str:
        return self.url.rstrip("/")

    def validate(self) -> None:
        if not self.url:
            raise ValueError("ODOO_URL is required")
        if not self.db:
            raise ValueError("ODOO_DB is required")
        if not self.api_key and not (self.username and self.password):
            raise ValueError(
                "Either ODOO_API_KEY or both ODOO_USERNAME and ODOO_PASSWORD are required"
            )


def load_config() -> OdooConfig:
    """Load configuration from environment variables."""
    load_dotenv()

    config = OdooConfig(
        url=os.getenv("ODOO_URL", "http://localhost:8069"),
        db=os.getenv("ODOO_DB", ""),
        username=os.getenv("ODOO_USERNAME"),
        password=os.getenv("ODOO_PASSWORD"),
        api_key=os.getenv("ODOO_API_KEY"),
    )
    config.validate()
    return config
