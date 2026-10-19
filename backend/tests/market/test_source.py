import asyncio
import logging

import pytest

from app.market import DEFAULT_TICKERS, PriceCache, SimulatorDataSource
from app.market.seed_prices import SEED_PRICES
from app.market.simulator import GBMSimulator


@pytest.fixture
async def running():
    """A started source with a fast interval; always stopped afterwards."""
    cache = PriceCache()
    source = SimulatorDataSource(cache, update_interval=0.02)
    await source.start(DEFAULT_TICKERS)
    yield cache, source
    await source.stop()


async def test_cache_seeded_before_start_returns(running):
    cache, _ = running
    prices = {t: u.price for t, u in cache.get_all().items()}
    assert set(prices) == set(DEFAULT_TICKERS)
    assert all(abs(prices[t] / SEED_PRICES[t] - 1) < 0.01 for t in prices)


async def test_loop_updates_cache(running):
    cache, _ = running
    version = cache.version
    await asyncio.sleep(0.15)
    assert cache.version > version


async def test_add_and_remove_ticker(running):
    cache, source = running
    await source.add_ticker("PYPL")
    assert "PYPL" in source.get_tickers()
    assert cache.get("PYPL") is not None
    await source.remove_ticker("PYPL")
    assert "PYPL" not in source.get_tickers()
    assert cache.get("PYPL") is None


async def test_stop_twice_and_version_freezes(running):
    cache, source = running
    await source.stop()
    await source.stop()
    version = cache.version
    await asyncio.sleep(0.1)
    assert cache.version == version


async def test_loop_survives_step_exception(monkeypatch, caplog):
    real_step = GBMSimulator.step
    calls = {"n": 0}

    def flaky(self):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("boom")
        return real_step(self)

    monkeypatch.setattr(GBMSimulator, "step", flaky)
    cache = PriceCache()
    source = SimulatorDataSource(cache, update_interval=0.02)
    await source.start(DEFAULT_TICKERS)
    version = cache.version
    with caplog.at_level(logging.ERROR):
        await asyncio.sleep(0.15)
    await source.stop()
    assert cache.version > version
    assert "Simulator step failed" in caplog.text
