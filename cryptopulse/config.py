"""
Central configuration for CryptoPulse.

Everything that might change between machines or environments (which coins to
track, email credentials, alert rules) is read from a .env file or the real
environment. Code NEVER hardcodes secrets — that keeps the public repo safe and
lets anyone clone it and supply their own values.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

# Load variables from a local .env file into the environment (if present).
# In production you might set real environment variables instead of a file.
load_dotenv()

# Project paths. We compute them relative to this file so the app works no
# matter what directory it is launched from.
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
REPORTS_DIR = BASE_DIR / "reports"
LOGS_DIR = BASE_DIR / "logs"

# Make sure the runtime directories exist before anything tries to write to them.
for _directory in (DATA_DIR, REPORTS_DIR, LOGS_DIR):
    _directory.mkdir(exist_ok=True)

DB_PATH = DATA_DIR / "cryptopulse.db"


def _split_csv(raw: str) -> list[str]:
    """Turn a comma-separated string into a clean list of non-empty items."""
    return [item.strip() for item in raw.split(",") if item.strip()]


@dataclass
class AlertRule:
    """A single price condition that can trigger a notification."""

    coin: str
    operator: str  # "above" or "below"
    threshold: float

    def is_triggered(self, price: float) -> bool:
        if self.operator == "above":
            return price > self.threshold
        if self.operator == "below":
            return price < self.threshold
        return False


@dataclass
class Settings:
    """All runtime settings, loaded once and passed around the app."""

    coins: list[str] = field(default_factory=list)
    vs_currency: str = "usd"

    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    alert_to: str = ""

    alert_rules: list[AlertRule] = field(default_factory=list)

    @property
    def email_enabled(self) -> bool:
        """Email is only active when the core SMTP fields are filled in."""
        return bool(self.smtp_host and self.smtp_user and self.smtp_password and self.alert_to)


def _parse_alert_rules(raw: str) -> list[AlertRule]:
    """Parse "bitcoin:above:80000,ethereum:below:2000" into AlertRule objects."""
    rules: list[AlertRule] = []
    for chunk in _split_csv(raw):
        parts = chunk.split(":")
        if len(parts) != 3:
            continue  # silently skip malformed rules rather than crashing
        coin, operator, threshold = parts
        try:
            rules.append(AlertRule(coin.strip(), operator.strip().lower(), float(threshold)))
        except ValueError:
            continue
    return rules


def load_settings() -> Settings:
    """Read configuration from the environment and return a Settings object."""
    return Settings(
        coins=_split_csv(os.getenv("COINS", "bitcoin,ethereum")),
        vs_currency=os.getenv("VS_CURRENCY", "usd").lower(),
        smtp_host=os.getenv("SMTP_HOST", ""),
        smtp_port=int(os.getenv("SMTP_PORT", "587")),
        smtp_user=os.getenv("SMTP_USER", ""),
        smtp_password=os.getenv("SMTP_PASSWORD", ""),
        alert_to=os.getenv("ALERT_TO", ""),
        alert_rules=_parse_alert_rules(os.getenv("ALERT_RULES", "")),
    )
