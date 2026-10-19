"""Repository functions for all tables.

Every function accepts an optional `conn`; pass the connection from `transaction()`
to group several writes atomically, or omit it to run in its own transaction.
"""

import json
import sqlite3

from .connection import new_id, now_iso, use

Conn = sqlite3.Connection | None


def get_cash(user_id: str = "default", conn: Conn = None) -> float:
    """Return the user's cash balance."""
    with use(conn) as c:
        row = c.execute("SELECT cash_balance FROM users_profile WHERE id = ?", (user_id,)).fetchone()
    return row["cash_balance"]


def set_cash(cash: float, user_id: str = "default", conn: Conn = None) -> None:
    """Set the user's cash balance."""
    with use(conn) as c:
        c.execute("UPDATE users_profile SET cash_balance = ? WHERE id = ?", (cash, user_id))


def get_watchlist(user_id: str = "default", conn: Conn = None) -> list[str]:
    """Return watched tickers in the order they were added."""
    with use(conn) as c:
        rows = c.execute(
            "SELECT ticker FROM watchlist WHERE user_id = ? ORDER BY added_at, rowid", (user_id,)
        ).fetchall()
    return [r["ticker"] for r in rows]


def add_to_watchlist(ticker: str, user_id: str = "default", conn: Conn = None) -> bool:
    """Add a ticker; return False if it was already present."""
    with use(conn) as c:
        cur = c.execute(
            "INSERT OR IGNORE INTO watchlist (id, user_id, ticker, added_at) VALUES (?, ?, ?, ?)",
            (new_id(), user_id, ticker, now_iso()),
        )
    return cur.rowcount == 1


def remove_from_watchlist(ticker: str, user_id: str = "default", conn: Conn = None) -> bool:
    """Remove a ticker; return False if it was absent."""
    with use(conn) as c:
        cur = c.execute("DELETE FROM watchlist WHERE user_id = ? AND ticker = ?", (user_id, ticker))
    return cur.rowcount == 1


def get_positions(user_id: str = "default", conn: Conn = None) -> list[dict]:
    """Return all positions as dicts with ticker, quantity, avg_cost, updated_at."""
    with use(conn) as c:
        rows = c.execute(
            "SELECT ticker, quantity, avg_cost, updated_at FROM positions"
            " WHERE user_id = ? ORDER BY ticker",
            (user_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def get_position(ticker: str, user_id: str = "default", conn: Conn = None) -> dict | None:
    """Return one position, or None if not held."""
    with use(conn) as c:
        row = c.execute(
            "SELECT ticker, quantity, avg_cost, updated_at FROM positions"
            " WHERE user_id = ? AND ticker = ?",
            (user_id, ticker),
        ).fetchone()
    return dict(row) if row else None


def upsert_position(
    ticker: str, quantity: float, avg_cost: float, user_id: str = "default", conn: Conn = None
) -> None:
    """Insert or replace the quantity and average cost of a position."""
    with use(conn) as c:
        c.execute(
            "INSERT INTO positions (id, user_id, ticker, quantity, avg_cost, updated_at)"
            " VALUES (?, ?, ?, ?, ?, ?)"
            " ON CONFLICT (user_id, ticker) DO UPDATE SET"
            " quantity = excluded.quantity, avg_cost = excluded.avg_cost,"
            " updated_at = excluded.updated_at",
            (new_id(), user_id, ticker, quantity, avg_cost, now_iso()),
        )


def delete_position(ticker: str, user_id: str = "default", conn: Conn = None) -> None:
    """Delete a position if it exists."""
    with use(conn) as c:
        c.execute("DELETE FROM positions WHERE user_id = ? AND ticker = ?", (user_id, ticker))


def record_trade(
    ticker: str,
    side: str,
    quantity: float,
    price: float,
    user_id: str = "default",
    conn: Conn = None,
) -> dict:
    """Append a trade and return it (id, ticker, side, quantity, price, executed_at)."""
    trade = {
        "id": new_id(),
        "ticker": ticker,
        "side": side,
        "quantity": quantity,
        "price": price,
        "executed_at": now_iso(),
    }
    with use(conn) as c:
        c.execute(
            "INSERT INTO trades (id, user_id, ticker, side, quantity, price, executed_at)"
            " VALUES (:id, :user_id, :ticker, :side, :quantity, :price, :executed_at)",
            {**trade, "user_id": user_id},
        )
    return trade


def get_trades(user_id: str = "default", limit: int = 50, conn: Conn = None) -> list[dict]:
    """Return the most recent trades, newest first."""
    with use(conn) as c:
        rows = c.execute(
            "SELECT id, ticker, side, quantity, price, executed_at FROM trades"
            " WHERE user_id = ? ORDER BY executed_at DESC, rowid DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
    return [dict(r) for r in rows]


def record_snapshot(total_value: float, user_id: str = "default", conn: Conn = None) -> None:
    """Record the portfolio's total value at the current time."""
    with use(conn) as c:
        c.execute(
            "INSERT INTO portfolio_snapshots (id, user_id, total_value, recorded_at)"
            " VALUES (?, ?, ?, ?)",
            (new_id(), user_id, total_value, now_iso()),
        )


def get_snapshots(user_id: str = "default", conn: Conn = None) -> list[dict]:
    """Return all snapshots (total_value, recorded_at), oldest first."""
    with use(conn) as c:
        rows = c.execute(
            "SELECT total_value, recorded_at FROM portfolio_snapshots"
            " WHERE user_id = ? ORDER BY recorded_at, rowid",
            (user_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def add_chat_message(
    role: str, content: str, actions: dict | None, user_id: str = "default", conn: Conn = None
) -> dict:
    """Store a chat message and return it (id, role, content, actions, created_at)."""
    msg = {"id": new_id(), "role": role, "content": content, "actions": actions,
           "created_at": now_iso()}
    with use(conn) as c:
        c.execute(
            "INSERT INTO chat_messages (id, user_id, role, content, actions, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (msg["id"], user_id, role, content,
             None if actions is None else json.dumps(actions), msg["created_at"]),
        )
    return msg


def get_chat_messages(user_id: str = "default", limit: int = 20, conn: Conn = None) -> list[dict]:
    """Return the most recent messages, oldest first, with actions parsed from JSON."""
    with use(conn) as c:
        rows = c.execute(
            "SELECT id, role, content, actions, created_at FROM chat_messages"
            " WHERE user_id = ? ORDER BY created_at DESC, rowid DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
    messages = [dict(r) for r in reversed(rows)]
    for m in messages:
        m["actions"] = None if m["actions"] is None else json.loads(m["actions"])
    return messages
