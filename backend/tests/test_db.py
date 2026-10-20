import sqlite3
import uuid

import pytest

from app import db
from app.market import DEFAULT_TICKERS

TABLES = {"users_profile", "watchlist", "positions", "trades", "portfolio_snapshots", "chat_messages"}


@pytest.fixture
def path(tmp_path, monkeypatch):
    p = tmp_path / "sub" / "t.db"
    monkeypatch.setenv("DB_PATH", str(p))
    return p


def test_init_creates_file_and_parent_dir(path):
    """init_db creates the missing parent directory and the DB file."""
    assert not path.parent.exists()
    db.init_db()
    assert path.exists()


def test_init_is_idempotent(path):
    """Re-running init_db neither duplicates the profile nor reseeds removed tickers."""
    db.init_db()
    db.init_db()
    db.remove_ticker("NFLX")
    db.init_db()
    with sqlite3.connect(path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM users_profile").fetchone()[0] == 1
    assert "NFLX" not in db.list_tickers()


def test_schema_tables(path):
    """All six tables exist with the default user_id."""
    db.init_db()
    with sqlite3.connect(path) as conn:
        names = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert names == TABLES
        for table in TABLES - {"users_profile"}:
            cols = {r[1]: r[4] for r in conn.execute(f"PRAGMA table_info({table})")}
            assert cols["user_id"] == "'default'"
        cols = {r[1]: r[4] for r in conn.execute("PRAGMA table_info(users_profile)")}
        assert cols["id"] == "'default'"


@pytest.mark.parametrize("table", ["watchlist", "positions"])
def test_schema_unique_user_ticker(path, table):
    """Inserting the same (user_id, ticker) twice violates the unique constraint."""
    db.init_db()
    cols = "id, user_id, ticker, " + ("quantity, avg_cost, updated_at" if table == "positions" else "added_at")
    tail = ", 1.0, 1.0, 'now'" if table == "positions" else ", 'now'"
    sql = f"INSERT INTO {table} ({cols}) VALUES (?, 'default', 'ZZZ'{tail})"
    with sqlite3.connect(path) as conn:
        conn.execute(sql, (str(uuid.uuid4()),))
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(sql, (str(uuid.uuid4()),))


def test_seed(path):
    """Fresh DB has the default profile and the ten default tickers in order."""
    db.init_db()
    with sqlite3.connect(path) as conn:
        row = conn.execute("SELECT id, cash_balance FROM users_profile").fetchone()
    assert row == ("default", 10000.0)
    assert db.list_tickers() == list(DEFAULT_TICKERS)
