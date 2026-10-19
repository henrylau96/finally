"""Portfolio REST endpoints."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app import db
from app.market import PriceCache
from app.portfolio import TradeError, execute_trade, get_portfolio


class TradeRequest(BaseModel):
    ticker: str
    quantity: float
    side: Literal["buy", "sell"]


def create_portfolio_router(price_cache: PriceCache) -> APIRouter:
    """Create the /api/portfolio router bound to the price cache."""
    router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])

    @router.get("")
    def read_portfolio() -> dict:
        return get_portfolio(price_cache)

    @router.post("/trade")
    def trade(req: TradeRequest) -> dict:
        try:
            result = execute_trade(req.ticker, req.side, req.quantity, price_cache)
        except TradeError as e:
            raise HTTPException(status_code=400, detail=str(e))
        return {"trade": result, "portfolio": get_portfolio(price_cache)}

    @router.get("/history")
    def history() -> list[dict]:
        return db.get_snapshots()

    return router
