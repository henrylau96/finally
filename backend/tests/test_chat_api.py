"""Real-LLM path through POST /api/chat: success and graceful failure."""

import pytest

from app.chat.router import FALLBACK


async def test_valid_reply_executes(client, llm_reply):
    llm_reply(content='{"message":"Done","trades":[{"ticker":"AAPL","side":"buy","quantity":1}],"watchlist_changes":[]}')
    r = await client.post("/api/chat", json={"message": "buy"})
    assert r.status_code == 200
    msg = r.json()["message"]
    assert msg["content"] == "Done"
    [a] = msg["actions"]
    assert a["ok"] is True and a["ticker"] == "AAPL"


@pytest.mark.parametrize(
    "kwargs",
    [
        {"content": "not json"},
        {"content": None},
        {"content": '{"msg":"x"}'},
        {"exc": RuntimeError("secret-key-xyz")},
    ],
    ids=["malformed", "none", "schema", "error"],
)
async def test_failures_are_graceful(client, llm_reply, kwargs):
    llm_reply(**kwargs)
    r = await client.post("/api/chat", json={"message": "hello"})
    assert r.status_code == 200
    assert "secret-key-xyz" not in r.text
    msg = r.json()["message"]
    assert msg["content"] == FALLBACK
    assert msg["actions"] == []
    hist = (await client.get("/api/chat/history")).json()
    assert [h["role"] for h in hist] == ["user", "assistant"]
