"""Health check endpoint reporting the running market data source."""

from fastapi import APIRouter

from app.market.interface import MarketDataSource


def create_health_router(source: MarketDataSource) -> APIRouter:
    """Build the health router; the body names the active source."""
    router = APIRouter()

    @router.get("/api/health")
    async def health() -> dict:
        return {"status": "ok", "source": source.name}

    return router
