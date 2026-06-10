"""
SQLite storage layer — the "store" stage of the pipeline.

A price you fetched and then forgot is almost useless. The moment we save every
snapshot to a database, CryptoPulse gains a memory: it can show how a coin moved
over hours and days, compute moving averages, and spot trends. That history is
the difference between a toy script and a real automation product.

Why SQLite?
  * It ships with Python — no server to install or run.
  * The whole database is a single file (data/cryptopulse.db) you can copy,
    back up, or inspect with any SQLite viewer.
  * It speaks standard SQL, so the concepts transfer directly to PostgreSQL,
    MySQL, etc. when a project outgrows it.

Automation skills demonstrated here:
  * Creating a schema safely (CREATE TABLE IF NOT EXISTS)
  * Parameterised SQL (?) that prevents SQL-injection and quoting bugs
  * Bulk inserts inside a single transaction (fast + all-or-nothing)
  * Indexes for fast lookups as the table grows
  * Using a context manager so connections always close cleanly
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Iterable, Iterator

from .api_client import PriceRecord
from .config import DB_PATH
from .logging_setup import get_logger

log = get_logger(__name__)

# The table that holds every price snapshot we ever fetch.
# Note the column types and that fetched_at is stored as ISO-8601 text, which
# sorts chronologically as plain text — a handy SQLite convention.
_SCHEMA = """
CREATE TABLE IF NOT EXISTS prices (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    coin        TEXT    NOT NULL,
    currency    TEXT    NOT NULL,
    price       REAL    NOT NULL,
    market_cap  REAL,
    change_24h  REAL,
    fetched_at  TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_prices_coin_time
    ON prices (coin, fetched_at);
"""


class PriceStore:
    """Reads and writes price history to a SQLite database file."""

    def __init__(self, db_path: Path = DB_PATH) -> None:
        self._db_path = db_path
        self._initialise()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        """Yield a connection that auto-commits on success and always closes.

        Using a context manager (`with self._connect() as conn:`) guarantees the
        connection is closed even if an error happens mid-operation — no leaked
        file handles, a common bug in long-running automation.
        """
        conn = sqlite3.connect(self._db_path)
        # Return rows as dict-like objects so we can access columns by name.
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()  # undo partial writes if anything went wrong
            raise
        finally:
            conn.close()

    def _initialise(self) -> None:
        """Create the table and index if they don't already exist."""
        with self._connect() as conn:
            conn.executescript(_SCHEMA)
        log.info("Database ready at %s", self._db_path)

    def save_prices(self, records: Iterable[PriceRecord]) -> int:
        """Insert many PriceRecords in one transaction. Returns the count saved.

        We build a list of tuples and use executemany for a single fast,
        atomic write — either all rows land or none do.
        """
        rows = [
            (
                r.coin,
                r.currency,
                r.price,
                r.market_cap,
                r.change_24h,
                r.fetched_at.isoformat(),
            )
            for r in records
        ]
        if not rows:
            log.info("save_prices called with nothing to save")
            return 0

        with self._connect() as conn:
            conn.executemany(
                """
                INSERT INTO prices
                    (coin, currency, price, market_cap, change_24h, fetched_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                rows,
            )
        log.info("Saved %d price record(s) to the database", len(rows))
        return len(rows)

    def latest_price(self, coin: str) -> float | None:
        """Return the most recent stored price for a coin, or None if unknown."""
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT price FROM prices
                WHERE coin = ?
                ORDER BY fetched_at DESC
                LIMIT 1
                """,
                (coin,),
            ).fetchone()
        return float(row["price"]) if row else None

    def history(self, coin: str, limit: int = 500) -> list[sqlite3.Row]:
        """Return recent snapshots for a coin, oldest first (for charting).

        We fetch the newest `limit` rows then reverse them so the timeline reads
        left-to-right (old → new), which is what charts expect.
        """
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT coin, price, market_cap, change_24h, fetched_at
                FROM prices
                WHERE coin = ?
                ORDER BY fetched_at DESC
                LIMIT ?
                """,
                (coin, limit),
            ).fetchall()
        return list(reversed(rows))

    def row_count(self) -> int:
        """Total number of snapshots stored — handy for status output."""
        with self._connect() as conn:
            row = conn.execute("SELECT COUNT(*) AS n FROM prices").fetchone()
        return int(row["n"])


# Quick smoke-test: fetch live prices and store them, then report the total.
# Run with:  python -m cryptopulse.storage
if __name__ == "__main__":
    from .api_client import CoinGeckoClient
    from .config import load_settings

    settings = load_settings()
    store = PriceStore()
    fetched = CoinGeckoClient().fetch_prices(settings.coins, settings.vs_currency)
    saved = store.save_prices(fetched)
    print(f"Saved {saved} new snapshot(s). Database now holds {store.row_count()} row(s).")
    for coin in settings.coins:
        print(f"  latest {coin}: {store.latest_price(coin)}")
