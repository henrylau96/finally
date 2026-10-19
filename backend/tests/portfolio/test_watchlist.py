"""Tests for the watchlist service."""

import pytest

from app import db
from app.market import PriceCache
from app.portfolio import (
    add_watchlist_ticker,
    execute_trade,
    get_watchlist_with_prices,
    normalize_ticker,
    remove_watchlist_ticker,
    tracked_tickers,
)


class FakeSource:
    def __init__(self):
        self.added, self.removed = [], []

    async def add_ticker(self, ticker):
        self.added.append(ticker)

    async def remove_ticker(self, ticker):
        self.removed.append(ticker)


@pytest.fixture(autouse=True)
def fresh_db(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    db.init_db()


def test_normalize_ticker():
    assert normalize_ticker(" brk.b ") == "BRK.B"
    for bad in ["", "TOOLONGTICKER", "AB1", "A-B"]:
        with pytest.raises(ValueError):
            normalize_ticker(bad)


async def test_add_starts_streaming():
    source = FakeSource()
    assert await add_watchlist_ticker("pypl", source) is True
    assert source.added == ["PYPL"]
    assert db.get_watchlist()[-1] == "PYPL"


async def test_add_duplicate_returns_false():
    source = FakeSource()
    assert await add_watchlist_ticker("AAPL", source) is False
    assert source.added == []


async def test_remove_stops_streaming():
    source = FakeSource()
    assert await remove_watchlist_ticker("aapl", source) is True
    assert source.removed == ["AAPL"]
    assert "AAPL" not in db.get_watchlist()


async def test_remove_absent_returns_false():
    assert await remove_watchlist_ticker("ZZZZ", FakeSource()) is False


async def test_remove_held_ticker_keeps_streaming():
    cache = PriceCache()
    cache.update("AAPL", 100.0)
    execute_trade("AAPL", "buy", 1, cache)
    source = FakeSource()
    assert await remove_watchlist_ticker("AAPL", source) is True
    assert source.removed == []
    assert "AAPL" in tracked_tickers()


def test_watchlist_with_prices():
    cache = PriceCache()
    cache.update("AAPL", 100.0)
    cache.update("AAPL", 101.0)
    rows = get_watchlist_with_prices(cache)
    assert [r["ticker"] for r in rows] == db.get_watchlist()
    aapl = rows[0]
    assert aapl["price"] == 101.0
    assert aapl["previous_price"] == 100.0
    assert aapl["direction"] == "up"
    assert rows[1]["price"] is None
