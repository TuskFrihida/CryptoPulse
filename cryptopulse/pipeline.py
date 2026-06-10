"""
The pipeline orchestrator — wires every stage into one repeatable cycle.

Each previous module did one job in isolation. This module is the conductor: it
runs them in order to perform a single, complete CryptoPulse cycle:

    fetch  →  store  →  analyze  →  build dashboard  →  check & alert

Keeping the orchestration here (separate from the CLI and scheduler) means the
"what happens in one run" logic lives in exactly one place and can be reused by
both a one-off command and the repeating scheduler.
"""

from __future__ import annotations

from dataclasses import dataclass

from .alerts import TriggeredAlert, check_and_alert
from .analysis import CoinSummary, summarise_all
from .api_client import CoinGeckoClient
from .config import Settings, load_settings
from .dashboard import build_dashboard
from .logging_setup import get_logger
from .storage import PriceStore

log = get_logger(__name__)


@dataclass
class CycleResult:
    """A summary of everything one pipeline cycle produced."""

    fetched: int
    stored: int
    summaries: list[CoinSummary]
    alerts: list[TriggeredAlert]
    dashboard_path: str


def run_cycle(settings: Settings | None = None, store: PriceStore | None = None) -> CycleResult:
    """Run one full fetch → store → analyze → dashboard → alert cycle.

    Returns a CycleResult so callers (CLI, tests) can report what happened.
    Network errors from the fetch are caught here so one bad cycle doesn't kill
    a long-running scheduler.
    """
    settings = settings or load_settings()
    store = store or PriceStore()

    log.info("=== Starting CryptoPulse cycle ===")

    # 1. FETCH
    try:
        records = CoinGeckoClient().fetch_prices(settings.coins, settings.vs_currency)
    except Exception as exc:  # noqa: BLE001 - we deliberately keep the loop alive
        log.error("Cycle aborted during fetch: %s", exc)
        return CycleResult(0, 0, [], [], "")

    # 2. STORE
    stored = store.save_prices(records)

    # 3. ANALYZE
    summaries = summarise_all(settings.coins, store)

    # 4. VISUALIZE
    dashboard_path = build_dashboard(settings.coins, settings.vs_currency, store)

    # 5. ALERT
    alerts = check_and_alert(summaries, settings)

    log.info(
        "=== Cycle complete: %d fetched, %d stored, %d alert(s) ===",
        len(records),
        stored,
        len(alerts),
    )

    return CycleResult(
        fetched=len(records),
        stored=stored,
        summaries=summaries,
        alerts=alerts,
        dashboard_path=str(dashboard_path),
    )
