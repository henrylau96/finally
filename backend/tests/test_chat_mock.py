"""Mock-mode chat API: replies, executed trades, validation."""

import pytest

from app.chat import mock


@pytest.fixture(autouse=True)
def mock_llm(monkeypatch):
    monkeypatch.setenv("LLM_MOCK", "true")


async def chat(client, text):
    return await client.post("/api/chat", json={"message": text})


async def cash(client):
    return (await client.get("/api/portfolio")).json()["cash_balance"]


async def test_mock_action_buy(client):
    before = await cash(client)
    r = await chat(client, "buy 1 AAPL")
    assert r.status_code == 200
    msg = r.json()["message"]
    assert msg["role"] == "assistant"
    assert msg["id"] and msg["created_at"]
    assert msg["content"].startswith("Mock response")
    [a] = msg["actions"]
    assert (a["type"], a["ticker"], a["side"], a["quantity"], a["ok"]) == ("trade", "AAPL", "buy", 1, True)
    assert isinstance(a["price"], float)
    assert await cash(client) < before


async def test_mock_plain_reply(client):
    r = await chat(client, "How is my portfolio doing?")
    assert r.status_code == 200
    msg = r.json()["message"]
    assert msg["content"].startswith("Mock response")
    assert msg["actions"] == []


@pytest.mark.parametrize("text", ["", "   ", "x" * 2001])
async def test_invalid_message_is_422(client, text):
    assert (await chat(client, text)).status_code == 422


def test_mock_regex_ignores_number_after_add():
    resp = mock.respond("add 5 AAPL")
    assert resp.watchlist_changes == []


def test_mock_regex_parses_fractional_quantity():
    [t] = mock.respond("sell 2.5 MSFT").trades
    assert (t.side, t.quantity, t.ticker) == ("sell", 2.5, "MSFT")
