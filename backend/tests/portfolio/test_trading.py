"""Tests for trade execution and portfolio valuation."""

import pytest

from app import db
from app.market import PriceCache
from app.portfolio import TradeError, execute_trade, get_portfolio


@pytest.fixture
def cache(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    db.init_db()
    cache = PriceCache()
    cache.update("AAPL", 100.0)
    return cache


def test_buy_deducts_cash_and_creates_position(cache):
    trade = execute_trade("aapl", "buy", 10, cache)
    assert trade["ticker"] == "AAPL"
    assert trade["price"] == 100.0
    assert db.get_cash() == pytest.approx(9000.0)
    pos = db.get_position("AAPL")
    assert pos["quantity"] == 10
    assert pos["avg_cost"] == 100.0


def test_weighted_average_cost(cache):
    execute_trade("AAPL", "buy", 10, cache)
    cache.update("AAPL", 130.0)
    execute_trade("AAPL", "buy", 20, cache)
    pos = db.get_position("AAPL")
    assert pos["quantity"] == 30
    assert pos["avg_cost"] == pytest.approx(120.0)


def test_insufficient_cash(cache):
    with pytest.raises(TradeError, match="Insufficient cash"):
        execute_trade("AAPL", "buy", 101, cache)
    assert db.get_cash() == 10000.0
    assert db.get_position("AAPL") is None
    assert db.get_trades() == []


def test_oversell(cache):
    execute_trade("AAPL", "buy", 5, cache)
    with pytest.raises(TradeError, match="Insufficient shares"):
        execute_trade("AAPL", "sell", 6, cache)
    assert db.get_position("AAPL")["quantity"] == 5


def test_sell_without_position(cache):
    with pytest.raises(TradeError, match="Insufficient shares"):
        execute_trade("AAPL", "sell", 1, cache)


def test_sell_to_zero_removes_position(cache):
    execute_trade("AAPL", "buy", 10, cache)
    execute_trade("AAPL", "sell", 10, cache)
    assert db.get_position("AAPL") is None
    assert db.get_cash() == pytest.approx(10000.0)


def test_sell_at_loss(cache):
    execute_trade("AAPL", "buy", 10, cache)
    cache.update("AAPL", 80.0)
    execute_trade("AAPL", "sell", 4, cache)
    assert db.get_cash() == pytest.approx(9000.0 + 320.0)
    pos = db.get_position("AAPL")
    assert pos["quantity"] == 6
    assert pos["avg_cost"] == 100.0


def test_fractional_shares(cache):
    execute_trade("AAPL", "buy", 0.5, cache)
    assert db.get_position("AAPL")["quantity"] == 0.5


@pytest.mark.parametrize("qty", [0, -1])
def test_non_positive_quantity(cache, qty):
    with pytest.raises(TradeError, match="greater than 0"):
        execute_trade("AAPL", "buy", qty, cache)


def test_unknown_price(cache):
    with pytest.raises(TradeError, match="No price"):
        execute_trade("ZZZZ", "buy", 1, cache)


def test_invalid_side(cache):
    with pytest.raises(TradeError, match="Invalid side"):
        execute_trade("AAPL", "short", 1, cache)


def test_trade_records_snapshot(cache):
    execute_trade("AAPL", "buy", 10, cache)
    snaps = db.get_snapshots()
    assert len(snaps) == 1
    assert snaps[0]["total_value"] == pytest.approx(10000.0)


def test_get_portfolio_pnl(cache):
    execute_trade("AAPL", "buy", 10, cache)
    cache.update("AAPL", 110.0)
    p = get_portfolio(cache)
    assert p["cash_balance"] == 9000.0
    assert p["total_value"] == 10100.0
    assert p["total_unrealized_pnl"] == 100.0
    pos = p["positions"][0]
    assert pos["market_value"] == 1100.0
    assert pos["unrealized_pnl"] == 100.0
    assert pos["unrealized_pnl_percent"] == 10.0
    assert pos["current_price"] == 110.0


def test_get_portfolio_falls_back_to_avg_cost(cache):
    execute_trade("AAPL", "buy", 10, cache)
    cache.remove("AAPL")
    pos = get_portfolio(cache)["positions"][0]
    assert pos["current_price"] == 100.0
    assert pos["unrealized_pnl"] == 0.0


@pytest.mark.parametrize("qty", [float("nan"), float("inf")])
def test_non_finite_quantity(cache, qty):
    with pytest.raises(TradeError, match="finite"):
        execute_trade("AAPL", "buy", qty, cache)
