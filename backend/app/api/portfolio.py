"""Portfolio and trade REST endpoints."""

import asyncio

from fastapi import APIRouter, HTTPException, Request

from app import portfolio, snapshots
from app.api.schemas import TradeRequest
from app.market.cache import PriceCache
from app.market.interface import MarketDataSource
from app.streaming import reconcile_stream


def create_portfolio_router(cache: PriceCache, source: MarketDataSource) -> APIRouter:
    router = APIRouter()

    @router.get("/api/portfolio")
    async def get_portfolio() -> dict:
        return await asyncio.to_thread(portfolio.portfolio_view, cache)

    @router.get("/api/portfolio/history")
    async def get_history() -> list[dict]:
        return await asyncio.to_thread(snapshots.history)

    @router.post("/api/portfolio/trade")
    async def trade(body: TradeRequest, request: Request) -> dict:
        try:
            if cache.get(body.ticker) is None:
                await source.add_ticker(body.ticker)
            async with request.app.state.trade_lock:
                update = cache.get(body.ticker)
                if update is None:
                    raise HTTPException(400, f"No price available for {body.ticker}")
                try:
                    result = await asyncio.to_thread(
                        portfolio.execute_trade, body.ticker, body.side, body.quantity, update.price
                    )
                except portfolio.TradeError as e:
                    raise HTTPException(400, str(e)) from e
            await asyncio.to_thread(snapshots.record_snapshot, cache)
            return result
        finally:
            await reconcile_stream(source, body.ticker)

    return router
