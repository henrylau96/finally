"""Portfolio and trade REST endpoints."""

import asyncio

from fastapi import APIRouter, HTTPException, Request

from app import portfolio
from app.api.schemas import TradeRequest
from app.market.cache import PriceCache
from app.market.interface import MarketDataSource


def create_portfolio_router(cache: PriceCache, source: MarketDataSource) -> APIRouter:
    router = APIRouter()

    @router.get("/api/portfolio")
    async def get_portfolio() -> dict:
        return await asyncio.to_thread(portfolio.portfolio_view, cache)

    @router.post("/api/portfolio/trade")
    async def trade(body: TradeRequest, request: Request) -> dict:
        if cache.get(body.ticker) is None:
            await source.add_ticker(body.ticker)
        async with request.app.state.trade_lock:
            update = cache.get(body.ticker)
            if update is None:
                raise HTTPException(400, f"No price available for {body.ticker}")
            try:
                return await asyncio.to_thread(
                    portfolio.execute_trade, body.ticker, body.side, body.quantity, update.price
                )
            except portfolio.TradeError as e:
                raise HTTPException(400, str(e)) from e

    return router
