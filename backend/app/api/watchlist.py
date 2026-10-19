"""Watchlist REST endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel

from app.market import MarketDataSource, PriceCache
from app.portfolio import add_watchlist_ticker, get_watchlist_with_prices, remove_watchlist_ticker


class WatchlistAdd(BaseModel):
    ticker: str


def create_watchlist_router(price_cache: PriceCache, source: MarketDataSource) -> APIRouter:
    """Create the /api/watchlist router bound to the price cache and market source."""
    router = APIRouter(prefix="/api/watchlist", tags=["watchlist"])

    @router.get("")
    def read_watchlist() -> list[dict]:
        return get_watchlist_with_prices(price_cache)

    @router.post("", status_code=201)
    async def add(req: WatchlistAdd) -> dict:
        try:
            added = await add_watchlist_ticker(req.ticker, source)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        ticker = req.ticker.upper().strip()
        if not added:
            raise HTTPException(status_code=409, detail=f"{ticker} is already in the watchlist")
        return {"ticker": ticker}

    @router.delete("/{ticker}", status_code=204)
    async def remove(ticker: str) -> Response:
        if not await remove_watchlist_ticker(ticker, source):
            raise HTTPException(status_code=404, detail=f"{ticker.upper()} is not in the watchlist")
        return Response(status_code=204)

    return router
