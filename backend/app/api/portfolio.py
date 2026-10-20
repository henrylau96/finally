"""Portfolio and trade REST endpoints."""

import asyncio

from fastapi import APIRouter, HTTPException, Request

from app import portfolio, services, snapshots
from app.api.schemas import TradeRequest
from app.market.cache import PriceCache
from app.market.interface import MarketDataSource


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
            return await services.place_trade(
                request.app, cache, source, body.ticker, body.side, body.quantity
            )
        except portfolio.TradeError as e:
            raise HTTPException(400, str(e)) from e

    return router
