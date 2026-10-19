"""Tests for chat orchestration: actions, failures, persistence, prompt context."""

import pytest

from app import db
from app.llm import chat
from app.llm.schema import ChatResponse, TradeAction, WatchlistAction


@pytest.fixture
def mock_mode(monkeypatch):
    monkeypatch.setenv("LLM_MOCK", "true")


async def test_mock_buy_executes(mock_mode, cache, source):
    body = await chat.handle_chat("buy 10 AAPL", cache, source)
    assert body["message"] == "Mock response: buy 10 AAPL"
    assert body["trades"] == [{"ticker": "AAPL", "side": "buy", "quantity": 10.0,
                               "status": "executed", "price": 100.0, "error": None}]
    assert body["watchlist_changes"] == []
    assert db.get_cash() == 9000.0
    assert db.get_position("AAPL")["quantity"] == 10.0


async def test_failed_trade_reported(mock_mode, cache, source):
    body = await chat.handle_chat("sell 5 AAPL", cache, source)
    trade = body["trades"][0]
    assert trade["status"] == "failed" and trade["error"] and trade["price"] is None
    assert db.get_cash() == 10000.0


async def test_insufficient_cash(mock_mode, cache, source):
    body = await chat.handle_chat("buy 1000 AAPL", cache, source)
    assert body["trades"][0]["status"] == "failed"


async def test_watchlist_changes(mock_mode, cache, source):
    body = await chat.handle_chat("add PYPL remove TSLA", cache, source)
    assert [c["status"] for c in body["watchlist_changes"]] == ["executed", "executed"]
    assert source.added == ["PYPL"] and source.removed == ["TSLA"]
    assert "PYPL" in db.get_watchlist() and "TSLA" not in db.get_watchlist()


async def test_watchlist_failures(mock_mode, cache, source):
    body = await chat.handle_chat("add AAPL remove ZZZZ", cache, source)
    assert [c["status"] for c in body["watchlist_changes"]] == ["failed", "failed"]
    assert all(c["error"] for c in body["watchlist_changes"])


async def test_messages_stored(mock_mode, cache, source):
    await chat.handle_chat("buy 1 AAPL", cache, source)
    user, assistant = db.get_chat_messages()
    assert (user["role"], user["content"], user["actions"]) == ("user", "buy 1 AAPL", None)
    assert assistant["role"] == "assistant"
    assert assistant["actions"]["trades"][0]["status"] == "executed"
    assert assistant["actions"]["watchlist_changes"] == []


async def test_real_path_builds_context(monkeypatch, cache, source):
    monkeypatch.setenv("LLM_MOCK", "false")
    db.add_chat_message("user", "earlier question", None)
    captured = {}

    async def fake_call_llm(messages):
        captured["messages"] = messages
        return ChatResponse(
            message="Bought",
            trades=[TradeAction(ticker="aapl", side="buy", quantity=2)],
            watchlist_changes=[WatchlistAction(ticker="PYPL", action="add")],
        )

    monkeypatch.setattr(chat, "call_llm", fake_call_llm)
    body = await chat.handle_chat("buy 2 apple", cache, source)

    messages = captured["messages"]
    assert "FinAlly" in messages[0]["content"]
    assert messages[1] == {"role": "user", "content": "earlier question"}
    assert messages[-2]["role"] == "system"
    assert '"cash_balance": 10000.0' in messages[-2]["content"]
    assert '"ticker": "AAPL"' in messages[-2]["content"]
    assert messages[-1] == {"role": "user", "content": "buy 2 apple"}
    assert body["message"] == "Bought"
    assert body["trades"][0]["ticker"] == "AAPL" and body["trades"][0]["status"] == "executed"
    assert body["watchlist_changes"][0]["status"] == "executed"


async def test_llm_error_returns_friendly_message(monkeypatch, cache, source):
    monkeypatch.setenv("LLM_MOCK", "false")

    async def failing_call_llm(messages):
        raise RuntimeError("auth failed")

    monkeypatch.setattr(chat, "call_llm", failing_call_llm)
    body = await chat.handle_chat("buy 1 AAPL", cache, source)
    assert body == {"message": chat.UNAVAILABLE_MESSAGE, "trades": [], "watchlist_changes": []}
    assert db.get_cash() == 10000.0
    assert [m["role"] for m in db.get_chat_messages()] == ["user", "assistant"]
