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


async def test_skipped_watchlist_action_keeps_next_turn_working(client, llm_reply):
    """A capped (skipped) watchlist action is replayable in the next turn's prompt."""
    adds = ",".join(f'{{"ticker":"A{c}","action":"add"}}' for c in "ABCDEFGHIJK")
    llm_reply(content=f'{{"message":"Added","watchlist_changes":[{adds}]}}')
    first = (await client.post("/api/chat", json={"message": "add 11"})).json()["message"]
    skipped = first["actions"][-1]
    assert skipped["action"] == "add" and skipped["ok"] is False and skipped["error"].startswith("Skipped")
    calls = llm_reply(content='{"message":"Fine"}')
    second = (await client.post("/api/chat", json={"message": "how am I doing?"})).json()["message"]
    assert second["content"] == "Fine" and len(calls) == 1
