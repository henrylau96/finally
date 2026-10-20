import asyncio

import pytest

from app.api import stream
from app.api.stream import price_events
from app.market.cache import PriceCache
from app.market.seed_prices import DEFAULT_TICKERS, SEED_PRICES

KEYS = {"ticker", "price", "previous_price", "timestamp", "direction", "day_change_pct"}


@pytest.fixture
def cache():
    c = PriceCache()
    for t in DEFAULT_TICKERS:
        c.update(t, SEED_PRICES[t])
    return c


async def test_first_event_has_all_tickers_and_retry(cache):
    """First event is a full snapshot carrying retry 1000."""
    event = await anext(price_events(cache, interval=0.01))
    assert set(event.data) == set(DEFAULT_TICKERS)
    assert all(set(v) == KEYS for v in event.data.values())
    assert event.retry == 1000


async def test_no_event_without_cache_change(cache):
    """No new event is emitted while the cache version is unchanged."""
    gen = price_events(cache, interval=0.01)
    await anext(gen)
    with pytest.raises(TimeoutError):
        await asyncio.wait_for(anext(gen), 0.1)


async def test_event_after_update_has_no_retry(cache):
    """A cache update triggers a second event without retry."""
    gen = price_events(cache, interval=0.01)
    await anext(gen)
    cache.update("AAPL", 191.0)
    event = await asyncio.wait_for(anext(gen), 1)
    assert event.retry is None


async def test_stream_ends_on_shutdown(cache, monkeypatch):
    """Setting the shutdown event ends the generator so the server can exit."""
    monkeypatch.setattr(stream, "shutdown", asyncio.Event())
    gen = price_events(cache, interval=0.01)
    await anext(gen)
    stream.shutdown.set()
    with pytest.raises(StopAsyncIteration):
        await asyncio.wait_for(anext(gen), 1)
