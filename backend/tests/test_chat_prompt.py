"""Prompt assembly and history windowing."""

from app import main
from app.chat import prompt, store

VALID = '{"message":"ok","trades":[],"watchlist_changes":[]}'


def test_build_messages_order():
    history = [
        {"role": "user", "content": "q1", "actions": None},
        {
            "role": "assistant",
            "content": "a1",
            "actions": [{"type": "trade", "ticker": "AAPL", "side": "buy", "quantity": 3, "price": 190.12, "ok": True}],
        },
    ]
    msgs = prompt.build_messages("CTX-BLOCK", history, "hi")
    assert msgs[0]["role"] == "system" and "FinAlly" in msgs[0]["content"]
    assert msgs[1]["role"] == "system" and "CTX-BLOCK" in msgs[1]["content"]
    assert [m["role"] for m in msgs[2:4]] == ["user", "assistant"]
    assert "bought 3 AAPL" in msgs[3]["content"]
    assert msgs[-1] == {"role": "user", "content": "hi"}


async def test_portfolio_context(client, seed_position):
    seed_position("AAPL", 3, 100.0)
    ctx = prompt.portfolio_context(main.cache)
    assert "Cash" in ctx and "AAPL" in ctx and "Watchlist" in ctx
    assert "Total value" in ctx


async def test_history_capped_at_20(client, llm_reply):
    for i in range(25):
        store.save_turn(f"u{i}", "2026-01-01T00:00:00+00:00", f"a{i}", [])
    calls = llm_reply(content=VALID)
    r = await client.post("/api/chat", json={"message": "brand-new"})
    assert r.status_code == 200
    msgs = calls[0]["messages"]
    assert len(msgs) == 2 + 20 + 1
    assert msgs[-1] == {"role": "user", "content": "brand-new"}
    assert sum("brand-new" in m["content"] for m in msgs) == 1
