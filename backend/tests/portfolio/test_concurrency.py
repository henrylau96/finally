"""Concurrent trades must not lose cash updates."""

import threading

import pytest

from app import db
from app.market import PriceCache
from app.portfolio import TradeError, execute_trade


def test_concurrent_buys_cannot_overspend(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    db.init_db()
    cache = PriceCache()
    cache.update("AAPL", 100.0)

    # Force both threads to read cash before either writes, if the DB allows it.
    barrier = threading.Barrier(2)
    real_get_cash = db.get_cash

    def get_cash_then_wait(*args, **kwargs):
        cash = real_get_cash(*args, **kwargs)
        try:
            barrier.wait(timeout=1)
        except threading.BrokenBarrierError:
            pass
        return cash

    monkeypatch.setattr(db, "get_cash", get_cash_then_wait)
    results = []

    def buy():
        try:
            execute_trade("AAPL", "buy", 60, cache)  # $6,000 each against $10,000
            results.append("ok")
        except TradeError:
            results.append("rejected")

    threads = [threading.Thread(target=buy) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    monkeypatch.setattr(db, "get_cash", real_get_cash)
    assert sorted(results) == ["ok", "rejected"]
    assert db.get_cash() == pytest.approx(4000.0)
    assert db.get_position("AAPL")["quantity"] == 60
