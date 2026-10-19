"""SQLite persistence layer: lazy init, transactions, and repository functions."""

from .connection import DEFAULT_TICKERS, get_db_path, init_db, transaction
from .repository import (
    add_chat_message,
    add_to_watchlist,
    delete_position,
    get_cash,
    get_chat_messages,
    get_position,
    get_positions,
    get_snapshots,
    get_trades,
    get_watchlist,
    record_snapshot,
    record_trade,
    remove_from_watchlist,
    set_cash,
    upsert_position,
)

__all__ = [
    "DEFAULT_TICKERS",
    "add_chat_message",
    "add_to_watchlist",
    "delete_position",
    "get_cash",
    "get_chat_messages",
    "get_db_path",
    "get_position",
    "get_positions",
    "get_snapshots",
    "get_trades",
    "get_watchlist",
    "init_db",
    "record_snapshot",
    "record_trade",
    "remove_from_watchlist",
    "set_cash",
    "transaction",
    "upsert_position",
]
