"""Background task that polls Massive REST and writes real prices into the cache."""

import asyncio
import contextlib
import logging
import time
from collections import deque
from datetime import date, datetime

from massive.exceptions import BadResponse

from app.market.cache import PriceCache
from app.market.interface import MarketDataSource
from app.market.massive_parse import (
    EOD_CALLS,
    EOD_MIN_INTERVAL,
    NY,
    RATE_WINDOW,
    Quote,
    bar_quote,
    daily_points,
    history_window,
    latest_grouped_bars,
    not_authorized,
    snapshot_quote,
)

logger = logging.getLogger(__name__)


def ny_today() -> date:
    """Today's date in New York, the exchange calendar."""
    return datetime.now(NY).date()


class MassiveDataSource(MarketDataSource):
    """Polls snapshots, or grouped daily bars on plans without snapshot access."""

    name = "massive"

    def __init__(self, cache: PriceCache, client, interval: float = 15.0) -> None:
        self._cache = cache
        self._client = client
        self._interval = interval
        self._mode = "snapshot"
        self._tickers: list[str] = []
        self._bars: dict = {}
        self._history: dict[str, tuple[date, list[dict]]] = {}
        self._history_lock = asyncio.Lock()
        self._api_lock = asyncio.Lock()
        self._calls: deque[float] = deque(maxlen=EOD_CALLS)
        self._task: asyncio.Task | None = None

    async def start(self, tickers: list[str]) -> None:
        """Fill the cache with a first poll, then start the poll loop."""
        self._tickers = list(tickers)
        await self._safe_poll()
        self._task = asyncio.create_task(self._run_loop(), name="massive-loop")

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None

    async def add_ticker(self, ticker: str) -> None:
        """Track a ticker and price it unless already priced; a failed fetch leaves no cache entry."""
        if ticker not in self._tickers:
            self._tickers.append(ticker)
        if self._cache.get(ticker):
            return
        try:
            quote = await self._fetch_one(ticker)
        except BadResponse as e:
            logger.error("Massive fetch failed for %s: %s", ticker, e)
            return
        except Exception:
            logger.exception("Massive fetch failed for %s", ticker)
            return
        if quote:
            self._write(ticker, quote)

    async def remove_ticker(self, ticker: str) -> None:
        if ticker in self._tickers:
            self._tickers.remove(ticker)
        self._cache.remove(ticker)

    async def history(self, ticker: str) -> list[dict]:
        """Daily closes, cached per ticker per NY day.

        A failed fetch returns [] uncached.
        """
        today = ny_today()
        cached = self._cached_history(ticker, today)
        if cached is not None:
            return cached
        async with self._history_lock:
            cached = self._cached_history(ticker, today)
            if cached is not None:
                return cached
            return await self._fetch_history(ticker, today)

    def _cached_history(self, ticker: str, today: date) -> list[dict] | None:
        cached = self._history.get(ticker)
        return cached[1] if cached and cached[0] == today else None

    async def _call(self, fn, *args, **kwargs):
        """Run one Massive request; in EOD mode keep to EOD_CALLS per RATE_WINDOW seconds."""
        async with self._api_lock:
            if self._mode == "eod" and len(self._calls) == EOD_CALLS:
                await asyncio.sleep(max(0.0, self._calls[0] + RATE_WINDOW - time.monotonic()))
            self._calls.append(time.monotonic())
            return await asyncio.to_thread(fn, *args, **kwargs)

    async def _fetch_history(self, ticker: str, today: date) -> list[dict]:
        start, end = history_window(today)
        try:
            aggs = await self._call(
                self._client.get_aggs, ticker, 1, "day", start, end, adjusted=True, sort="asc"
            )
        except BadResponse as e:
            logger.error("Massive history failed for %s: %s", ticker, e)
            return []
        except Exception:
            logger.exception("Massive history failed for %s", ticker)
            return []
        points = daily_points(aggs)
        self._history[ticker] = (today, points)
        return points

    def get_tickers(self) -> list[str]:
        return list(self._tickers)

    async def _fetch_one(self, ticker: str) -> Quote | None:
        """One ticker's quote: snapshot, cached grouped bar, or previous close.

        A snapshot entitlement error switches to EOD mode and falls through.
        """
        if self._mode == "snapshot":
            try:
                snap = await self._call(self._client.get_snapshot_ticker, "stocks", ticker)
                return snapshot_quote(snap)
            except Exception as e:
                if not not_authorized(e):
                    raise
                self._enter_eod()
        if ticker in self._bars:
            return bar_quote(self._bars[ticker])
        bars = await self._call(self._client.get_previous_close_agg, ticker, adjusted=True)
        return bar_quote(bars[0]) if bars else None

    def _enter_eod(self) -> None:
        """Switch to end-of-day bars after a snapshot entitlement error."""
        logger.warning("Massive snapshots not authorized, using end-of-day bars")
        self._mode = "eod"
        self._interval = max(self._interval, EOD_MIN_INTERVAL)

    async def _poll_once(self) -> None:
        """Poll every tracked ticker; switch to EOD once on a snapshot entitlement error."""
        if not self._tickers:
            return
        if self._mode == "snapshot":
            try:
                snaps = await self._call(
                    self._client.get_snapshot_all, "stocks", tickers=self._tickers
                )
            except Exception as e:
                if not not_authorized(e):
                    raise
                self._enter_eod()
            else:
                for snap in snaps:
                    quote = snapshot_quote(snap)
                    if quote and snap.ticker in self._tickers:
                        self._write(snap.ticker, quote)
                return
        await self._poll_eod()

    async def _poll_eod(self) -> None:
        """Fetch the latest grouped bars and write the tracked tickers."""
        self._bars = await latest_grouped_bars(self._grouped, ny_today())
        for ticker in self._tickers:
            if ticker in self._bars:
                self._write(ticker, bar_quote(self._bars[ticker]))

    async def _grouped(self, day: str) -> list:
        """One rate-limited grouped daily bars request."""
        return await self._call(self._client.get_grouped_daily_aggs, day, adjusted=True)

    def _write(self, ticker: str, quote: Quote) -> None:
        """Cache a quote unless it repeats the cached price and time."""
        price, ts, ref = quote
        cur = self._cache.get(ticker)
        if cur and cur.timestamp == ts and cur.price == round(price, 2):
            return
        self._cache.update(ticker, price, timestamp=ts, reference=ref)

    async def _run_loop(self) -> None:
        while True:
            await asyncio.sleep(self._interval)
            await self._safe_poll()

    async def _safe_poll(self) -> None:
        """Poll once; an API error logs one line, anything else a traceback."""
        try:
            await self._poll_once()
        except BadResponse as e:
            logger.error("Massive poll failed: %s", e)
        except Exception:
            logger.exception("Massive poll failed")
