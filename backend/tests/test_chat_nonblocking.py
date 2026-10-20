"""CHAT-09: a slow LLM call never blocks the event loop; chat actions and manual trades don't deadlock."""

import asyncio
import time

from app import main


async def test_stream_continues_during_slow_llm(client, llm_reply):
    llm_reply(content='{"message":"ok","trades":[],"watchlist_changes":[]}', delay=1.6)
    gaps = []

    async def ticker():
        last = time.perf_counter()
        while True:
            await asyncio.sleep(0.02)
            now = time.perf_counter()
            gaps.append(now - last)
            last = now

    async def health_mid_call():
        await asyncio.sleep(0.8)
        start = time.perf_counter()
        r = await client.get("/api/health")
        return r.status_code, time.perf_counter() - start

    before = main.cache.version
    task = asyncio.create_task(ticker())
    chat, (status, took) = await asyncio.gather(
        client.post("/api/chat", json={"message": "hello"}), health_mid_call()
    )
    task.cancel()
    assert chat.status_code == 200
    assert status == 200 and took < 0.3
    assert main.cache.version >= before + 2
    assert max(gaps) < 0.3


async def test_chat_actions_and_manual_trade_do_not_deadlock(client, monkeypatch):
    monkeypatch.setenv("LLM_MOCK", "true")
    chat, trade = await asyncio.wait_for(
        asyncio.gather(
            client.post("/api/chat", json={"message": "add PYPL buy 1 PYPL"}),
            client.post("/api/portfolio/trade", json={"ticker": "AAPL", "side": "buy", "quantity": 1}),
        ),
        timeout=5,
    )
    assert chat.status_code == 200 and trade.status_code == 200
    actions = chat.json()["message"]["actions"]
    assert len(actions) == 2 and all(a["ok"] for a in actions)
