"""FastAPI routes for the chat assistant."""

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app import db
from app.market import MarketDataSource, PriceCache

from .chat import handle_chat


class ChatRequest(BaseModel):
    """Body of POST /api/chat."""

    message: str = Field(min_length=1)


def create_chat_router(price_cache: PriceCache, market_source: MarketDataSource) -> APIRouter:
    """Create the router providing POST /api/chat and GET /api/chat/history."""
    router = APIRouter(prefix="/api/chat", tags=["chat"])

    @router.post("")
    async def chat(request: ChatRequest) -> dict:
        return await handle_chat(request.message, price_cache, market_source)

    @router.get("/history")
    async def history() -> list[dict]:
        return db.get_chat_messages(limit=100)

    return router
