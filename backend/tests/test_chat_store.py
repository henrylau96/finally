"""Chat persistence and history endpoint."""

import pytest

from app import db
from app.chat import store


@pytest.fixture(autouse=True)
def mock_llm(monkeypatch):
    monkeypatch.setenv("LLM_MOCK", "true")


async def chat(client, text):
    return await client.post("/api/chat", json={"message": text})


async def test_history_oldest_first_with_roles(client):
    await chat(client, "hello")
    await chat(client, "again")
    rows = (await client.get("/api/chat/history")).json()
    assert [r["role"] for r in rows] == ["user", "assistant", "user", "assistant"]
    assert rows[0]["content"] == "hello"
    assert rows[0]["actions"] is None
    assert rows[1]["actions"] == []


async def test_actions_round_trip(client):
    actions = [{"type": "trade", "ticker": "AAPL", "side": "buy", "quantity": 1, "ok": True}]
    store.save_turn("buy 1 AAPL", "2026-01-01T00:00:00+00:00", "done", actions)
    rows = (await client.get("/api/chat/history")).json()
    assert rows[-1]["actions"] == actions
    assert rows[-2]["actions"] is None


def test_history_limit_50(db_env):
    db.init_db()
    for i in range(30):
        store.save_turn(f"q{i}", "2026-01-01T00:00:00+00:00", f"a{i}", [])
    rows = store.history()
    assert len(rows) == 50
    assert rows[-1]["content"] == "a29"
