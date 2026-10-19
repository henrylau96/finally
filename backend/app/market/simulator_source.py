"""Background task that feeds simulated prices into the cache."""

import asyncio
import contextlib
import logging

from app.market.cache import PriceCache
from app.market.simulator import GBMSimulator

logger = logging.getLogger(__name__)


class SimulatorDataSource:
    """Runs GBMSimulator on an interval and writes each step to the cache."""

    def __init__(self, cache: PriceCache, update_interval: float = 0.5) -> None:
        self._cache = cache
        self._interval = update_interval
        self._sim: GBMSimulator | None = None
        self._task: asyncio.Task | None = None

    async def start(self, tickers: list[str]) -> None:
        """Seed the cache, then start the update loop."""
        self._sim = GBMSimulator(tickers)
        for t in tickers:
            self._cache.update(t, self._sim.get_price(t))
        self._task = asyncio.create_task(self._run_loop(), name="simulator-loop")

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None

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
