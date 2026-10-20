"""Chat action execution: shared validation, ordering, caps."""

from contextlib import closing

import pytest

from app import db, main
from app.chat.execute import run_actions
from app.chat.schema import ChatResponse, TradeAction


@pytest.fixture(autouse=True)
def mock_llm(monkeypatch):
    monkeypatch.setenv("LLM_MOCK", "true")


async def chat(client, text):
    r = await client.post("/api/chat", json={"message": text})
    assert r.status_code == 200
    return r.json()["message"]["actions"]


async def cash(client):
    return (await client.get("/api/portfolio")).json()["cash_balance"]


def trade_count():
    with closing(db.connect(db.db_path())) as conn:
        return conn.execute("SELECT COUNT(*) FROM trades").fetchone()[0]


async def test_insufficient_cash_action(client):
    before, n = await cash(client), trade_count()
    [a] = await chat(client, "buy 1000000 AAPL")
    assert a["ok"] is False and a["error"].startswith("Insufficient cash")
    assert await cash(client) == before and trade_count() == n


async def test_oversell_action(client):
    [a] = await chat(client, "sell 5 TSLA")
    assert a["ok"] is False and a["error"].startswith("Cannot sell")


async def test_add_then_buy_action(client):
    acts = await chat(client, "add PYPL buy 2 PYPL")
    assert [(a["type"], a["ok"]) for a in acts] == [("watchlist", True), ("trade", True)]
    tickers = [w["ticker"] for w in (await client.get("/api/watchlist")).json()]
    assert "PYPL" in tickers
    positions = (await client.get("/api/portfolio")).json()["positions"]
    assert [p["quantity"] for p in positions if p["ticker"] == "PYPL"] == [2]


async def test_duplicate_add_action(client):
    [a] = await chat(client, "add AAPL")
    assert a["ok"] is True


async def test_remove_unwatched_action(client):
    [a] = await chat(client, "remove PYPL")
    assert a["ok"] is False and a["error"] == "Ticker not on watchlist"


async def test_action_cap(client):
    resp = ChatResponse(message="x", trades=[TradeAction(ticker="AAPL", side="buy", quantity=0.01)] * 12)
    out = await run_actions(main.app, main.cache, main.source, resp)
    assert len(out) == 12
    assert [a["ok"] for a in out[-2:]] == [False, False]
    assert out[-1]["error"] == "Skipped: at most 10 actions per reply"
    assert all(a["ok"] for a in out[:10])


@pytest.mark.parametrize("ticker,qty", [("TOOLONG", 1), ("AAPL", -1), ("AAPL", 0.00001)])
async def test_invalid_trade_action(client, ticker, qty):
    n = trade_count()
    resp = ChatResponse(message="x", trades=[TradeAction(ticker=ticker, side="buy", quantity=qty)])
    [a] = await run_actions(main.app, main.cache, main.source, resp)
    assert a["ok"] is False
    assert a["error"] == "Invalid trade (ticker 1-5 letters, quantity > 0, max 4 decimals)"
    assert trade_count() == n


async def test_unexpected_action_error_keeps_turn(client, monkeypatch):
    """An unexpected error in one action is recorded; earlier actions and the turn are kept."""
    from app import services

    async def boom(*args, **kwargs):
        raise RuntimeError("database is locked")

    monkeypatch.setattr(services, "place_trade", boom)
    acts = await chat(client, "add PYPL buy 2 PYPL")
    assert [(a["type"], a["ok"]) for a in acts] == [("watchlist", True), ("trade", False)]
    assert acts[1]["error"] == "Action failed unexpectedly"
    hist = (await client.get("/api/chat/history")).json()
    assert [h["role"] for h in hist] == ["user", "assistant"]
