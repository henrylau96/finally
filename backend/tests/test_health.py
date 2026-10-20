import httpx
from fastapi import FastAPI

from app.api.health import create_health_router
from app.main import app
from app.market import PriceCache
from app.market.massive_source import MassiveDataSource


async def get_health(target: FastAPI) -> httpx.Response:
    """GET /api/health on the given app."""
    transport = httpx.ASGITransport(app=target)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.get("/api/health")


async def test_health_returns_ok_and_source():
    """Health endpoint reports ok and the simulator source under tests."""
    response = await get_health(app)
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "source": "simulator"}


async def test_health_reports_massive():
    """Health reports "massive" when built with the Massive source (never started)."""
    target = FastAPI()
    target.include_router(create_health_router(MassiveDataSource(PriceCache(), object())))
    response = await get_health(target)
    assert response.json() == {"status": "ok", "source": "massive"}
