"""Fixtures for LLM chat tests."""

import pytest

from app import db
from app.market import PriceCache


class FakeSource:
    """Records add/remove calls instead of streaming prices."""

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


@pytest.fixture
def cache():
    cache = PriceCache()
    cache.update("AAPL", 100.0)
    return cache


@pytest.fixture
def source():
    return FakeSource()
