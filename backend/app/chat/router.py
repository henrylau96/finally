"""Chat endpoints: send a message, read history."""

import asyncio
import logging
from datetime import UTC, datetime

from fastapi import APIRouter, Request

from app.chat import llm, mock, prompt, store
from app.chat.execute import run_actions
from app.chat.schema import ChatRequest, ChatResponse
from app.market.cache import PriceCache
from app.market.interface import MarketDataSource

logger = logging.getLogger(__name__)

FALLBACK = "Sorry, I couldn't process that. Please try again."


def create_chat_router(cache: PriceCache, source: MarketDataSource) -> APIRouter:
    router = APIRouter()

    @router.post("/api/chat")
    async def chat(body: ChatRequest, request: Request) -> dict:
        user_at = datetime.now(UTC).isoformat()
        ctx, hist = await asyncio.gather(
            asyncio.to_thread(prompt.portfolio_context, cache), asyncio.to_thread(store.history, 20)
        )
        if mock.mock_enabled():
            resp = mock.respond(body.message)
        else:
            try:
                resp = await llm.complete(prompt.build_messages(ctx, hist, body.message))
            except Exception:
                logger.exception("chat LLM call failed")
                resp = ChatResponse(message=FALLBACK)
        actions = await run_actions(request.app, cache, source, resp)
        row = await asyncio.to_thread(store.save_turn, body.message, user_at, resp.message, actions)
        return {"message": row}

    @router.get("/api/chat/history")
    async def chat_history() -> list[dict]:
        return await asyncio.to_thread(store.history)

    return router
