"""Tests for REST routes: status codes and response shapes."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app import db
from app.api import create_portfolio_router, create_watchlist_router, health_router
from app.market import PriceCache


class FakeSource:
    async def add_ticker(self, ticker):
        pass

    async def remove_ticker(self, ticker):
        pass


@pytest.fixture
def cache():
    cache = PriceCache()
    cache.update("AAPL", 100.0)
    return cache


@pytest.fixture
def client(tmp_path, monkeypatch, cache):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    db.init_db()
    app = FastAPI()
    app.include_router(health_router)
    app.include_router(create_portfolio_router(cache))
    app.include_router(create_watchlist_router(cache, FakeSource()))
    return TestClient(app)


def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok"}


def test_empty_portfolio(client):
    r = client.get("/api/portfolio")
    assert r.status_code == 200
    assert r.json() == {
        "cash_balance": 10000.0,
        "total_value": 10000.0,
        "total_unrealized_pnl": 0.0,
        "positions": [],
    }


def test_trade_buy(client):
    r = client.post("/api/portfolio/trade", json={"ticker": "aapl", "quantity": 10, "side": "buy"})
    assert r.status_code == 200
    body = r.json()
    assert set(body["trade"]) >= {"id", "ticker", "side", "quantity", "price", "executed_at"}
    assert body["trade"]["ticker"] == "AAPL"
    assert body["portfolio"]["cash_balance"] == 9000.0
    pos = body["portfolio"]["positions"][0]
    assert set(pos) == {
        "ticker", "quantity", "avg_cost", "current_price",
        "market_value", "unrealized_pnl", "unrealized_pnl_percent",
    }


def test_trade_insufficient_cash(client):
    r = client.post("/api/portfolio/trade", json={"ticker": "AAPL", "quantity": 1000, "side": "buy"})
    assert r.status_code == 400
    assert "Insufficient cash" in r.json()["detail"]


def test_trade_oversell(client):
    r = client.post("/api/portfolio/trade", json={"ticker": "AAPL", "quantity": 1, "side": "sell"})
    assert r.status_code == 400


def test_trade_bad_side(client):
    r = client.post("/api/portfolio/trade", json={"ticker": "AAPL", "quantity": 1, "side": "x"})
    assert r.status_code == 422


def test_history(client):
    client.post("/api/portfolio/trade", json={"ticker": "AAPL", "quantity": 1, "side": "buy"})
    r = client.get("/api/portfolio/history")
    assert r.status_code == 200
    snaps = r.json()
    assert len(snaps) == 1
    assert set(snaps[0]) == {"total_value", "recorded_at"}


def test_get_watchlist(client):
    rows = client.get("/api/watchlist").json()
    assert len(rows) == 10
    assert rows[0]["ticker"] == "AAPL"
    assert rows[0]["price"] == 100.0
    assert set(rows[0]) == {"ticker", "price", "previous_price", "change", "change_percent", "direction"}
    assert rows[1]["price"] is None


def test_add_watchlist(client):
    r = client.post("/api/watchlist", json={"ticker": "pypl"})
    assert r.status_code == 201
    assert r.json() == {"ticker": "PYPL"}
    assert client.get("/api/watchlist").json()[-1]["ticker"] == "PYPL"


def test_add_watchlist_duplicate(client):
    assert client.post("/api/watchlist", json={"ticker": "AAPL"}).status_code == 409


def test_add_watchlist_invalid(client):
    assert client.post("/api/watchlist", json={"ticker": "BAD1"}).status_code == 400


def test_remove_watchlist(client):
    assert client.delete("/api/watchlist/aapl").status_code == 204
    assert client.delete("/api/watchlist/AAPL").status_code == 404
