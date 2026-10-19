"""SQLite connection handling, transactions, and lazy schema initialization."""

import os
import sqlite3
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SCHEMA_PATH = Path(__file__).with_name("schema.sql")
DEFAULT_TICKERS = ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA", "NVDA", "META", "JPM", "V", "NFLX"]
DEFAULT_CASH = 10000.0


def get_db_path() -> Path:
    """Return the database path from env DB_PATH, or <repo>/db/finally.db."""
    return Path(os.environ.get("DB_PATH") or REPO_ROOT / "db" / "finally.db")


def now_iso() -> str:
    """Current UTC time as an ISO 8601 string."""
    return datetime.now(UTC).isoformat()


def new_id() -> str:
    """New random UUID string."""
    return str(uuid.uuid4())


def connect() -> sqlite3.Connection:
    """Open a connection with dict-like rows, creating the parent directory."""
    path = get_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def transaction() -> Iterator[sqlite3.Connection]:
    """Yield a connection; commit on success, roll back on error, always close."""
    conn = connect()
    try:
        with conn:
            yield conn
    finally:
        conn.close()


@contextmanager
def use(conn: sqlite3.Connection | None) -> Iterator[sqlite3.Connection]:
    """Reuse a caller's connection (their transaction) or open a fresh one."""
    if conn is not None:
        yield conn
    else:
        with transaction() as fresh:
            yield fresh


def init_db(user_id: str = "default") -> None:
    """Create tables if missing and seed the default user and watchlist. Idempotent."""
    with transaction() as conn:
        conn.executescript(SCHEMA_PATH.read_text())
        created = conn.execute(
            "INSERT OR IGNORE INTO users_profile (id, cash_balance, created_at) VALUES (?, ?, ?)",
            (user_id, DEFAULT_CASH, now_iso()),
        ).rowcount
        if created:
            conn.executemany(
                "INSERT INTO watchlist (id, user_id, ticker, added_at) VALUES (?, ?, ?, ?)",
                [(new_id(), user_id, t, now_iso()) for t in DEFAULT_TICKERS],
            )
