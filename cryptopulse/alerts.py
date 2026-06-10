"""
Email alerts — the "act" stage of the pipeline.

Fetching, storing, and charting are all passive. Alerts are where automation
starts working *for* you: CryptoPulse checks each coin against the price rules
you defined in .env and emails you the moment one is crossed — no staring at a
screen required.

We use Python's built-in smtplib and email modules (no extra dependency) to
send mail over SMTP. The classic use case is a Gmail "App Password", but any
SMTP server works.

Automation skills demonstrated here:
  * Evaluating user-defined rules against live data
  * Composing a proper MIME email (plain-text + HTML parts)
  * Sending mail securely over SMTP with STARTTLS encryption
  * Failing safe: if email isn't configured, we log and move on (never crash)
"""

from __future__ import annotations

import smtplib
from dataclasses import dataclass
from email.message import EmailMessage

from .analysis import CoinSummary
from .config import AlertRule, Settings
from .logging_setup import get_logger

log = get_logger(__name__)


@dataclass
class TriggeredAlert:
    """Records that a specific rule fired against a specific price."""

    rule: AlertRule
    price: float

    def describe(self) -> str:
        return f"{self.rule.coin} is {self.rule.operator} {self.rule.threshold:,.2f} (now {self.price:,.2f})"


def evaluate_rules(summaries: list[CoinSummary], rules: list[AlertRule]) -> list[TriggeredAlert]:
    """Check every rule against the latest prices and return the ones that fire.

    We index summaries by coin for a quick lookup, then ask each rule's own
    is_triggered() method whether it should fire. Keeping the condition logic
    inside AlertRule (Step 1) keeps this function simple.
    """
    latest_by_coin = {s.coin: s.latest_price for s in summaries}
    triggered: list[TriggeredAlert] = []

    for rule in rules:
        price = latest_by_coin.get(rule.coin)
        if price is None:
            continue  # we have no current price for this coin; skip
        if rule.is_triggered(price):
            triggered.append(TriggeredAlert(rule=rule, price=price))
            log.info("Alert triggered: %s", TriggeredAlert(rule, price).describe())

    return triggered


def _compose_email(alerts: list[TriggeredAlert], settings: Settings) -> EmailMessage:
    """Build a multipart (plain-text + HTML) alert email."""
    msg = EmailMessage()
    msg["Subject"] = f"🚨 CryptoPulse: {len(alerts)} price alert(s) triggered"
    msg["From"] = settings.smtp_user
    msg["To"] = settings.alert_to

    lines = [a.describe() for a in alerts]
    text_body = "CryptoPulse price alerts:\n\n" + "\n".join(f"  • {line}" for line in lines)

    html_items = "".join(f"<li>{line}</li>" for line in lines)
    html_body = (
        "<h2>🚨 CryptoPulse price alerts</h2>"
        f"<ul>{html_items}</ul>"
        "<p style='color:#888'>Sent automatically by CryptoPulse.</p>"
    )

    # Set the plain-text part first, then add the HTML alternative. Mail clients
    # show the richest part they support, falling back to text.
    msg.set_content(text_body)
    msg.add_alternative(html_body, subtype="html")
    return msg


def send_alerts(alerts: list[TriggeredAlert], settings: Settings) -> bool:
    """Email the triggered alerts. Returns True if mail was sent.

    Fails safe: if there's nothing to send or email isn't configured, we log
    and return False rather than raising — a missing SMTP password should never
    crash a scheduled run.
    """
    if not alerts:
        log.info("No alerts triggered; nothing to send")
        return False

    if not settings.email_enabled:
        log.warning("Email not configured (.env); skipping send of %d alert(s)", len(alerts))
        return False

    msg = _compose_email(alerts, settings)

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as server:
            server.starttls()  # upgrade the connection to encrypted TLS
            server.login(settings.smtp_user, settings.smtp_password)
            server.send_message(msg)
    except (smtplib.SMTPException, OSError) as exc:
        # Network/auth problems are logged, not fatal — the next cycle retries.
        log.error("Failed to send alert email: %s", exc)
        return False

    log.info("Sent alert email with %d alert(s) to %s", len(alerts), settings.alert_to)
    return True


def check_and_alert(summaries: list[CoinSummary], settings: Settings) -> list[TriggeredAlert]:
    """Convenience: evaluate rules and send any that fire. Returns the alerts."""
    triggered = evaluate_rules(summaries, settings.alert_rules)
    send_alerts(triggered, settings)
    return triggered


# Smoke-test the rule engine WITHOUT sending real email, using fake data so it
# runs anywhere. Run with:  python -m cryptopulse.alerts
if __name__ == "__main__":
    from datetime import datetime, timezone

    demo_summaries = [
        CoinSummary("bitcoin", 85_000.0, 3.1, 82_000.0, "up", 10),
        CoinSummary("ethereum", 1_900.0, -4.2, 2_050.0, "down", 10),
    ]
    demo_rules = [
        AlertRule("bitcoin", "above", 80_000.0),
        AlertRule("ethereum", "below", 2_000.0),
        AlertRule("bitcoin", "below", 1.0),  # won't fire
    ]
    fired = evaluate_rules(demo_summaries, demo_rules)
    print(f"{len(fired)} rule(s) fired:")
    for a in fired:
        print(f"  • {a.describe()}")
    print("\n(Configure SMTP_* in .env to actually receive these by email.)")
