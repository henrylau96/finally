"""Chat endpoints: send a message, read history."""

import asyncio
from datetime import UTC, datetime

from fastapi import APIRouter, Request

from app.chat import mock, store
from app.chat.execute import run_actions
from app.chat.schema import ChatRequest, ChatResponse
from app.market.cache import PriceCache
from app.market.interface import MarketDataSource

FALLBACK = "Sorry, I couldn't process that. Please try again."


def create_chat_router(cache: PriceCache, source: MarketDataSource) -> APIRouter:
    router = APIRouter()

    @router.post("/api/chat")
    async def chat(body: ChatRequest, request: Request) -> dict:
        user_at = datetime.now(UTC).isoformat()
        resp = mock.respond(body.message) if mock.mock_enabled() else ChatResponse(message=FALLBACK)
        actions = await run_actions(request.app, cache, source, resp)
        row = await asyncio.to_thread(store.save_turn, body.message, user_at, resp.message, actions)
        return {"message": row}

    @router.get("/api/chat/history")
    async def chat_history() -> list[dict]:
        return await asyncio.to_thread(store.history)

    return router
