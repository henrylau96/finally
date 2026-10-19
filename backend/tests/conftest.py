import httpx
import pytest

from app import main


@pytest.fixture
def db_env(tmp_path, monkeypatch):
    """Point DB_PATH at a fresh temp file and empty the shared price cache."""
    path = tmp_path / "test.db"
    monkeypatch.setenv("DB_PATH", str(path))
    for ticker in list(main.cache.get_all()):
        main.cache.remove(ticker)
    return path


@pytest.fixture
async def client(db_env):
    """HTTP client against the app with its lifespan running on a temp DB."""
    async with main.app.router.lifespan_context(main.app):
        transport = httpx.ASGITransport(app=main.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            yield c
