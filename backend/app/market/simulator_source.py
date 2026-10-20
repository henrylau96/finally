"""Background task that feeds simulated prices into the cache."""

import asyncio
import contextlib
import logging

from app.market.cache import PriceCache
from app.market.interface import MarketDataSource
from app.market.simulator import GBMSimulator

logger = logging.getLogger(__name__)


class SimulatorDataSource(MarketDataSource):
    """Runs GBMSimulator on an interval and writes each step to the cache."""

    name = "simulator"

    def __init__(
        self, cache: PriceCache, update_interval: float = 0.5, event_probability: float = 0.001
    ) -> None:
        self._cache = cache
        self._interval = update_interval
        self._event_prob = event_probability
        self._sim: GBMSimulator | None = None
        self._task: asyncio.Task | None = None

    async def start(self, tickers: list[str]) -> None:
        """Seed the cache, then start the update loop."""
        self._sim = GBMSimulator(tickers, event_probability=self._event_prob)
        for t in tickers:
            self._cache.update(t, self._sim.get_price(t))
        self._task = asyncio.create_task(self._run_loop(), name="simulator-loop")

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None

    async def add_ticker(self, ticker: str) -> None:
        if ticker in self._sim.tickers:
            return
        self._sim.add_ticker(ticker)
        self._cache.update(ticker, self._sim.get_price(ticker))

    async def remove_ticker(self, ticker: str) -> None:
        self._sim.remove_ticker(ticker)
        self._cache.remove(ticker)

    async def history(self, ticker: str) -> list[dict]:
        """The simulator has no past; the chart fills from the stream."""
        return []

    def get_tickers(self) -> list[str]:
        return self._sim.tickers if self._sim else []

    async def _run_loop(self) -> None:
        while True:
            try:
                for ticker, price in self._sim.step().items():
                    self._cache.update(ticker, price)
            except Exception:
                logger.exception("Simulator step failed")
            await asyncio.sleep(self._interval)
