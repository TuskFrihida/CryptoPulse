"""
Market analysis — the "analyze" stage of the pipeline.

Storing prices gives us raw numbers. Analysis turns those numbers into meaning:
  * How has each coin's price moved recently?
  * What is its trend, smoothed of noise (a moving average)?
  * Which coins are the biggest movers right now?

We use pandas, the standard Python library for working with tabular data. The
core object is the DataFrame — think of it as a spreadsheet in memory, with
powerful one-line operations for filtering, grouping, and computing.

Automation skills demonstrated here:
  * Loading SQL query results straight into a pandas DataFrame
  * Parsing timestamps and sorting time-series data
  * Rolling-window calculations (moving averages) for trend smoothing
  * Aggregating per group (one summary row per coin)
  * Returning clean, typed summaries the dashboard and alerts can reuse
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .config import DB_PATH
from .logging_setup import get_logger
from .storage import PriceStore

log = get_logger(__name__)


@dataclass
class CoinSummary:
    """A compact, human-friendly summary of one coin's current state."""

    coin: str
    latest_price: float
    change_24h: float | None
    moving_avg: float | None  # short-term trend line value
    trend: str  # "up", "down", or "flat" vs. the moving average
    samples: int  # how many stored snapshots this summary is based on


def load_history_df(coin: str, store: PriceStore | None = None) -> pd.DataFrame:
    """Load one coin's stored history into a tidy, time-sorted DataFrame.

    The DataFrame has a proper datetime index so pandas' time-series tools
    (rolling windows, resampling) work naturally.
    """
    store = store or PriceStore()
    rows = store.history(coin)
    if not rows:
        return pd.DataFrame()

    # sqlite3.Row objects behave like dicts, so pandas can build a frame from
    # a list of them directly.
    df = pd.DataFrame([dict(r) for r in rows])
    df["fetched_at"] = pd.to_datetime(df["fetched_at"])
    df = df.sort_values("fetched_at").set_index("fetched_at")
    return df


def add_moving_average(df: pd.DataFrame, window: int = 5) -> pd.DataFrame:
    """Add a rolling moving-average column that smooths out short-term noise.

    A moving average is the average of the last `window` prices, recomputed at
    each point. It's the simplest, most widely used trend indicator: when price
    sits above its moving average the trend is up, below it the trend is down.
    """
    if df.empty:
        return df
    df = df.copy()
    # min_periods=1 means we still get a value early on, before we have a full
    # window of data — useful when history is just starting to build up.
    df["moving_avg"] = df["price"].rolling(window=window, min_periods=1).mean()
    return df


def summarise_coin(coin: str, store: PriceStore | None = None, window: int = 5) -> CoinSummary | None:
    """Build a CoinSummary for a single coin, or None if we have no data yet."""
    df = load_history_df(coin, store)
    if df.empty:
        log.info("No history yet for %s; cannot summarise", coin)
        return None

    df = add_moving_average(df, window=window)

    latest_price = float(df["price"].iloc[-1])
    moving_avg = float(df["moving_avg"].iloc[-1])
    change_24h = df["change_24h"].iloc[-1]
    change_24h = None if pd.isna(change_24h) else float(change_24h)

    # Decide the trend by comparing the latest price to its moving average,
    # using a small dead-band (0.1%) so tiny wiggles count as "flat".
    deadband = moving_avg * 0.001
    if latest_price > moving_avg + deadband:
        trend = "up"
    elif latest_price < moving_avg - deadband:
        trend = "down"
    else:
        trend = "flat"

    return CoinSummary(
        coin=coin,
        latest_price=latest_price,
        change_24h=change_24h,
        moving_avg=moving_avg,
        trend=trend,
        samples=len(df),
    )


def summarise_all(coins: list[str], store: PriceStore | None = None, window: int = 5) -> list[CoinSummary]:
    """Summarise every coin, skipping any that have no stored data yet."""
    store = store or PriceStore()
    summaries = [summarise_coin(c, store, window) for c in coins]
    return [s for s in summaries if s is not None]


def top_movers(summaries: list[CoinSummary], n: int = 3) -> list[CoinSummary]:
    """Return the `n` coins with the largest absolute 24h move.

    "Movers" means biggest change in either direction, so we sort by the
    absolute value of change_24h. Coins missing that figure sort last.
    """
    def magnitude(s: CoinSummary) -> float:
        return abs(s.change_24h) if s.change_24h is not None else -1.0

    return sorted(summaries, key=magnitude, reverse=True)[:n]


# Smoke-test: summarise whatever the database currently holds.
# Run with:  python -m cryptopulse.analysis
if __name__ == "__main__":
    from .config import load_settings

    settings = load_settings()
    results = summarise_all(settings.coins)
    if not results:
        print("No data stored yet. Run 'python -m cryptopulse.storage' first.")
    else:
        for s in results:
            change = f"{s.change_24h:+.2f}%" if s.change_24h is not None else "n/a"
            print(
                f"{s.coin:>10} | price {s.latest_price:>12,.2f} | "
                f"MA {s.moving_avg:>12,.2f} | trend {s.trend:<4} | "
                f"24h {change:>8} | {s.samples} samples"
            )
        print("\nTop movers:")
        for s in top_movers(results):
            change = f"{s.change_24h:+.2f}%" if s.change_24h is not None else "n/a"
            print(f"  {s.coin} ({change})")
