"""Massive (Polygon.io) API client for real market data."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from massive import RESTClient
from massive.exceptions import BadResponse
from massive.rest.models import TickerSnapshot

from .cache import PriceCache
from .interface import MarketDataSource

logger = logging.getLogger(__name__)

MARKET_TZ = ZoneInfo("America/New_York")

PriceAndTime = tuple[float, float | None]


def snapshot_price(snap: TickerSnapshot) -> PriceAndTime | None:
    """Best available (price, unix_seconds) from a snapshot, or None.

    last_trade is only present on plans with trades (Developer+); Starter
    falls back to the latest minute bar. day.close is 0 before the open.
    """
    if snap.last_trade and snap.last_trade.price:
        return snap.last_trade.price, snap.last_trade.sip_timestamp / 1e9  # ns
    if snap.min and snap.min.close:
        return snap.min.close, snap.min.timestamp / 1e3  # ms
    if snap.day and snap.day.close:
        return snap.day.close, None
    if snap.prev_day and snap.prev_day.close:
        return snap.prev_day.close, None
    return None


def latest_eod_closes(client: RESTClient, max_days_back: int = 5) -> dict[str, float]:
    """Close prices for all US stocks from the most recent trading day with data.

    Starts from yesterday in New York time: free plans reject the current
    market date until end of day, whatever the local timezone.
    """
    day = datetime.now(MARKET_TZ).date() - timedelta(days=1)
    for _ in range(max_days_back):
        bars = client.get_grouped_daily_aggs(day.isoformat(), adjusted=True)
        if bars:
            return {b.ticker: b.close for b in bars if b.close}
        day -= timedelta(days=1)
    return {}


class MassiveDataSource(MarketDataSource):
    """MarketDataSource backed by the Massive (Polygon.io) REST API.

    Two modes, each one API call per poll regardless of ticker count:
      - snapshot: GET /v2/snapshot/locale/us/markets/stocks/tickers (Starter+)
      - eod: GET /v2/aggs/grouped/locale/us/market/stocks/{date} (all plans)

    Starts in snapshot mode and switches to eod permanently if the plan is
    not entitled to snapshots (free tier returns 403 NOT_AUTHORIZED).
    """

    def __init__(
        self,
        api_key: str,
        price_cache: PriceCache,
        poll_interval: float = 15.0,
        eod_poll_interval: float = 900.0,
    ) -> None:
        self._api_key = api_key
        self._cache = price_cache
        self._interval = poll_interval
        self._eod_interval = eod_poll_interval
        self._mode = "snapshot"
        self._eod_closes: dict[str, float] = {}
        self._tickers: list[str] = []
        self._task: asyncio.Task | None = None
        self._client: RESTClient | None = None

    async def start(self, tickers: list[str]) -> None:
        self._client = RESTClient(api_key=self._api_key)
        self._tickers = [t.upper().strip() for t in tickers]

        # Do an immediate first poll so the cache has data right away
        await self._poll_once()

        self._task = asyncio.create_task(self._poll_loop(), name="massive-poller")
        logger.info(
            "Massive poller started: %d tickers, %s mode, %.1fs interval",
            len(self._tickers),
            self._mode,
            self._interval,
        )

    async def stop(self) -> None:
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._task = None
        self._client = None
        logger.info("Massive poller stopped")

    async def add_ticker(self, ticker: str) -> None:
        ticker = ticker.upper().strip()
        if ticker not in self._tickers:
            self._tickers.append(ticker)
            # In eod mode the last grouped response already holds every ticker
            if ticker in self._eod_closes:
                self._cache.update(ticker=ticker, price=self._eod_closes[ticker])
            logger.info("Massive: added ticker %s", ticker)

    async def remove_ticker(self, ticker: str) -> None:
        ticker = ticker.upper().strip()
        self._tickers = [t for t in self._tickers if t != ticker]
        self._cache.remove(ticker)
        logger.info("Massive: removed ticker %s", ticker)

    def get_tickers(self) -> list[str]:
        return list(self._tickers)

    # --- Internal ---

    async def _poll_loop(self) -> None:
        """Poll on interval. First poll already happened in start()."""
        while True:
            await asyncio.sleep(self._interval)
            await self._poll_once()

    async def _poll_once(self) -> None:
        """Execute one poll cycle: fetch prices, update cache. Never raises."""
        if not self._tickers or not self._client:
            return

        try:
            # The Massive RESTClient is synchronous; run it off the event loop.
            prices = await asyncio.to_thread(self._fetch)
        except BadResponse as e:
            if self._mode == "snapshot" and "NOT_AUTHORIZED" in str(e):
                logger.warning("Massive plan has no snapshot access; using end-of-day prices")
                self._mode = "eod"
                self._interval = self._eod_interval
                await self._poll_once()
            else:
                logger.error("Massive poll failed: %s", e)
            return
        except Exception as e:
            # Network errors etc. The loop retries on the next interval.
            logger.error("Massive poll failed: %s", e)
            return

        for ticker, (price, timestamp) in prices.items():
            self._cache.update(ticker=ticker, price=price, timestamp=timestamp)
        logger.debug("Massive poll: updated %d/%d tickers", len(prices), len(self._tickers))

    def _fetch(self) -> dict[str, PriceAndTime]:
        """Synchronous fetch for the current mode. Runs in a thread."""
        if self._mode == "snapshot":
            # Must be the plain string: the SDK formats SnapshotMarketType (a
            # plain Enum) into the URL as "SnapshotMarketType.STOCKS" -> 404.
            snapshots = self._client.get_snapshot_all(
                market_type="stocks",
                tickers=self._tickers,
            )
            return {s.ticker: p for s in snapshots if (p := snapshot_price(s))}

        self._eod_closes = latest_eod_closes(self._client)
        return {t: (self._eod_closes[t], None) for t in self._tickers if t in self._eod_closes}
