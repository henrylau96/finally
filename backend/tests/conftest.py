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


@pytest.fixture
def seed_position(db_env):
    """Return seed(ticker, quantity, avg_cost, cash=None) inserting a position into a fresh DB."""
    from contextlib import closing
    from datetime import UTC, datetime
    from uuid import uuid4

    from app import db

    def seed(ticker, quantity, avg_cost, cash=None):
        db.init_db()
        with closing(db.connect(db.db_path())) as conn, conn:
            conn.execute(
                "INSERT INTO positions (id, user_id, ticker, quantity, avg_cost, updated_at) "
                "VALUES (?, 'default', ?, ?, ?, ?) "
                "ON CONFLICT(user_id, ticker) DO UPDATE SET quantity=excluded.quantity, "
                "avg_cost=excluded.avg_cost, updated_at=excluded.updated_at",
                (str(uuid4()), ticker, quantity, avg_cost, datetime.now(UTC).isoformat()),
            )
            if cash is not None:
                conn.execute("UPDATE users_profile SET cash_balance = ?", (cash,))

    return seed
