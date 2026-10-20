"""Daily price history for seeding the main chart."""

from fastapi import APIRouter, HTTPException

from app.api.schemas import normalize_ticker
from app.market.interface import MarketDataSource


def create_history_router(source: MarketDataSource) -> APIRouter:
    """Build the history router over the active market data source."""
    router = APIRouter()

    @router.get("/api/history/{ticker}")
    async def history(ticker: str) -> list[dict]:
        try:
            t = normalize_ticker(ticker)
        except ValueError:
            raise HTTPException(422, "ticker must be 1-5 letters")
        return await source.history(t)

    return router
