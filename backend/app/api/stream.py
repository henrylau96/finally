"""SSE price stream."""

import asyncio
from collections.abc import AsyncIterable, AsyncIterator

from fastapi import APIRouter
from fastapi.sse import EventSourceResponse, ServerSentEvent

from app.market.cache import PriceCache


async def price_events(cache: PriceCache, interval: float = 0.5) -> AsyncIterator[ServerSentEvent]:
    """Yield a full price snapshot whenever the cache version changes."""
    last_version, retry = -1, 1000
    while True:
        if cache.version != last_version:
            last_version = cache.version
            payload = {t: u.to_dict() for t, u in cache.get_all().items()}
            yield ServerSentEvent(data=payload, retry=retry)
            retry = None
        await asyncio.sleep(interval)


def create_stream_router(cache: PriceCache, interval: float = 0.5) -> APIRouter:
    router = APIRouter()

    @router.get("/api/stream/prices", response_class=EventSourceResponse)
    async def stream_prices() -> AsyncIterable[ServerSentEvent]:
        async for event in price_events(cache, interval):
            yield event

    return router
