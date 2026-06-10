"""
CoinGecko API client — the "fetch" stage of the pipeline.

This module is the only place in CryptoPulse that talks to the outside world.
Isolating network access in one file is a deliberate design choice: if the API
ever changes, or we want to swap CoinGecko for another provider, we only touch
this file. The rest of the app just asks for "the latest prices" and gets back
clean Python objects.

Key automation skills demonstrated here:
  * Calling a REST API with the `requests` library
  * Adding a timeout so a hung server can never freeze our program forever
  * Automatic retries with backoff for flaky networks / rate limits
  * Converting messy JSON into typed, predictable objects (PriceRecord)
  * Defensive parsing that won't crash on missing fields
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .logging_setup import get_logger

log = get_logger(__name__)

# The free, no-API-key-required CoinGecko endpoint.
_BASE_URL = "https://api.coingecko.com/api/v3"

# Never wait longer than this (seconds) for the server to respond. A timeout is
# the single most important habit in network automation: without it, one slow
# server can hang your scheduled job indefinitely.
_TIMEOUT = 15


@dataclass
class PriceRecord:
    """One coin's price snapshot at a single moment in time.

    This is the clean, typed shape the rest of the app works with — no raw JSON
    dictionaries leak out of this module.
    """

    coin: str
    currency: str
    price: float
    market_cap: float | None
    change_24h: float | None
    fetched_at: datetime  # always UTC, so timestamps are comparable everywhere


def _build_session() -> requests.Session:
    """Create a requests Session that retries automatically on transient errors.

    A Session reuses the underlying TCP connection across calls (faster) and
    lets us attach a retry policy. We retry on 429 (rate limited) and the 5xx
    server errors, backing off a little longer each attempt so we don't hammer
    a struggling server.
    """
    session = requests.Session()
    retry = Retry(
        total=3,
        backoff_factor=1.0,  # waits 0s, 1s, 2s between tries
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET",),
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    # A descriptive User-Agent is good etiquette and helps APIs identify us.
    session.headers.update({"User-Agent": "CryptoPulse/0.1 (+https://github.com/TuskFrihida/CryptoPulse)"})
    return session


class CoinGeckoClient:
    """A thin, well-behaved wrapper around the CoinGecko price API."""

    def __init__(self, session: requests.Session | None = None) -> None:
        # Accepting an optional session makes the client easy to test: a fake
        # session can be injected. If none is given, we build a real one.
        self._session = session or _build_session()

    def fetch_prices(self, coins: list[str], vs_currency: str = "usd") -> list[PriceRecord]:
        """Fetch current prices for the given coins.

        Returns a list of PriceRecord objects (one per coin the API knew about).
        Coins the API doesn't recognize are simply skipped, not fatal.
        """
        if not coins:
            log.warning("fetch_prices called with no coins; returning empty list")
            return []

        params = {
            "ids": ",".join(coins),
            "vs_currencies": vs_currency,
            "include_market_cap": "true",
            "include_24hr_change": "true",
            "include_last_updated_at": "true",
        }

        url = f"{_BASE_URL}/simple/price"
        log.info("Fetching prices for %s in %s", coins, vs_currency)

        try:
            response = self._session.get(url, params=params, timeout=_TIMEOUT)
            response.raise_for_status()  # turn HTTP 4xx/5xx into an exception
        except requests.RequestException as exc:
            # We log and re-raise: the caller (scheduler) decides whether one
            # failed cycle should stop everything (it won't — see Step 7).
            log.error("Price request failed: %s", exc)
            raise

        payload = response.json()
        records = self._parse_payload(payload, vs_currency)
        log.info("Fetched %d price record(s)", len(records))
        return records

    @staticmethod
    def _parse_payload(payload: dict, vs_currency: str) -> list[PriceRecord]:
        """Turn the raw JSON dict into a list of PriceRecord objects.

        Example payload shape:
            {"bitcoin": {"usd": 61133, "usd_market_cap": 1.2e12,
                         "usd_24h_change": -2.67, "last_updated_at": 1781083769}}
        """
        now = datetime.now(timezone.utc)
        records: list[PriceRecord] = []

        for coin, data in payload.items():
            # The API names its fields with the currency baked in, e.g. "usd",
            # "usd_market_cap", "usd_24h_change". We build those keys here.
            price = data.get(vs_currency)
            if price is None:
                # No price means nothing useful to store — skip this coin.
                log.warning("No %s price returned for %s; skipping", vs_currency, coin)
                continue

            records.append(
                PriceRecord(
                    coin=coin,
                    currency=vs_currency,
                    price=float(price),
                    market_cap=_as_float(data.get(f"{vs_currency}_market_cap")),
                    change_24h=_as_float(data.get(f"{vs_currency}_24h_change")),
                    fetched_at=now,
                )
            )
        return records


def _as_float(value: object) -> float | None:
    """Safely convert a value to float, returning None if it can't be done."""
    if value is None:
        return None
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


# Running `python -m cryptopulse.api_client` does a quick live smoke-test so you
# can see real data flow through the client without the rest of the app.
if __name__ == "__main__":
    from .config import load_settings

    settings = load_settings()
    client = CoinGeckoClient()
    for record in client.fetch_prices(settings.coins, settings.vs_currency):
        print(
            f"{record.coin:>10} = {record.price:>12,.2f} {record.currency.upper()} "
            f"(24h: {record.change_24h:+.2f}%)"
        )
