"""SQLite repository: schema creation, seeding and watchlist queries."""

import os
import sqlite3
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from app.market.seed_prices import DEFAULT_TICKERS

SCHEMA = Path(__file__).parents[1] / "db" / "schema.sql"
DEFAULT_DB = Path(__file__).parents[2] / "db" / "finally.db"


def db_path() -> Path:
    """Return the database path from DB_PATH, read at call time."""
    return Path(os.environ.get("DB_PATH", DEFAULT_DB))


def connect(path: Path) -> sqlite3.Connection:
    """Open a connection returning rows addressable by column name."""
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create the file, schema and (for a brand new profile) the seed data."""
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with closing(connect(path)) as conn:
        conn.execute("PRAGMA journal_mode=WAL")
    with closing(connect(path)) as conn, conn:
        conn.executescript(SCHEMA.read_text())
        if conn.execute("SELECT COUNT(*) FROM users_profile").fetchone()[0] == 0:
            seed(conn)


def seed(conn: sqlite3.Connection) -> None:
    """Insert the default profile with $10,000 and the default watchlist."""
    now = datetime.now(UTC).isoformat()
    conn.execute(
        "INSERT INTO users_profile (id, cash_balance, created_at) VALUES ('default', 10000.0, ?)",
        (now,),
    )
    conn.executemany(
        "INSERT INTO watchlist (id, user_id, ticker, added_at) VALUES (?, 'default', ?, ?)",
        [(str(uuid4()), t, now) for t in DEFAULT_TICKERS],
    )


def list_watchlist() -> list[dict]:
    """Return watchlist rows (ticker, added_at) in insertion order."""
    with closing(connect(db_path())) as conn, conn:
        rows = conn.execute(
            "SELECT ticker, added_at FROM watchlist WHERE user_id = 'default' ORDER BY rowid"
        ).fetchall()
    return [dict(r) for r in rows]


def list_tickers() -> list[str]:
    """Return watched tickers in insertion order."""
    return [r["ticker"] for r in list_watchlist()]


def add_ticker(ticker: str) -> tuple[dict, bool]:
    """Insert a ticker if absent; return its row and whether it was created."""
    now = datetime.now(UTC).isoformat()
    with closing(connect(db_path())) as conn, conn:
        cur = conn.execute(
            "INSERT OR IGNORE INTO watchlist (id, user_id, ticker, added_at) "
            "VALUES (?, 'default', ?, ?)",
            (str(uuid4()), ticker, now),
        )
        row = conn.execute(
            "SELECT ticker, added_at FROM watchlist WHERE user_id = 'default' AND ticker = ?",
            (ticker,),
        ).fetchone()
    return dict(row), cur.rowcount == 1


def remove_ticker(ticker: str) -> bool:
    """Delete a ticker; return whether a row was removed."""
    with closing(connect(db_path())) as conn, conn:
        cur = conn.execute(
            "DELETE FROM watchlist WHERE user_id = 'default' AND ticker = ?", (ticker,)
        )
    return cur.rowcount == 1
