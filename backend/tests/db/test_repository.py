"""Tests for repository CRUD functions."""

import sqlite3

import pytest

from app import db


def test_set_cash():
    db.set_cash(1234.5)
    assert db.get_cash() == 1234.5


def test_add_to_watchlist_appends_in_order():
    assert db.add_to_watchlist("PYPL") is True
    assert db.get_watchlist()[-1] == "PYPL"


def test_add_duplicate_returns_false():
    assert db.add_to_watchlist("AAPL") is False
    assert db.get_watchlist().count("AAPL") == 1


def test_remove_from_watchlist():
    assert db.remove_from_watchlist("TSLA") is True
    assert "TSLA" not in db.get_watchlist()
    assert db.remove_from_watchlist("TSLA") is False


def test_watchlist_is_per_user():
    db.add_to_watchlist("PYPL", user_id="bob")
    assert db.get_watchlist("bob") == ["PYPL"]
    assert "PYPL" not in db.get_watchlist()


def test_position_upsert_get_delete():
    assert db.get_position("AAPL") is None
    db.upsert_position("AAPL", 10, 190.0)
    db.upsert_position("AAPL", 15, 192.0)
    pos = db.get_position("AAPL")
    assert pos["quantity"] == 15
    assert pos["avg_cost"] == 192.0
    assert pos["updated_at"]
    assert len(db.get_positions()) == 1
    db.delete_position("AAPL")
    assert db.get_position("AAPL") is None


def test_get_positions_fields():
    db.upsert_position("MSFT", 2.5, 400.0)
    db.upsert_position("AAPL", 1, 190.0)
    positions = db.get_positions()
    assert [p["ticker"] for p in positions] == ["AAPL", "MSFT"]
    assert set(positions[0]) == {"ticker", "quantity", "avg_cost", "updated_at"}


def test_unique_constraints_enforced(tmp_db):
    conn = sqlite3.connect(tmp_db)
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO watchlist (id, user_id, ticker, added_at) VALUES ('x', 'default', 'AAPL', 't')"
        )
    conn.execute(
        "INSERT INTO positions (id, user_id, ticker, quantity, avg_cost, updated_at)"
        " VALUES ('p1', 'default', 'AAPL', 1, 1, 't')"
    )
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO positions (id, user_id, ticker, quantity, avg_cost, updated_at)"
            " VALUES ('p2', 'default', 'AAPL', 1, 1, 't')"
        )
    conn.close()


def test_record_and_get_trades():
    first = db.record_trade("AAPL", "buy", 10, 190.0)
    second = db.record_trade("AAPL", "sell", 4, 195.0)
    assert set(first) == {"id", "ticker", "side", "quantity", "price", "executed_at"}
    trades = db.get_trades()
    assert [t["id"] for t in trades] == [second["id"], first["id"]]
    assert trades[1] == first
    assert len(db.get_trades(limit=1)) == 1


def test_invalid_trade_side_rejected():
    with pytest.raises(sqlite3.IntegrityError):
        db.record_trade("AAPL", "hold", 1, 1.0)


def test_snapshots_ascending():
    db.record_snapshot(10000.0)
    db.record_snapshot(10050.0)
    snaps = db.get_snapshots()
    assert [s["total_value"] for s in snaps] == [10000.0, 10050.0]
    assert set(snaps[0]) == {"total_value", "recorded_at"}


def test_chat_actions_round_trip():
    actions = {"trades": [{"ticker": "AAPL", "side": "buy", "quantity": 1, "status": "executed"}],
               "watchlist_changes": []}
    db.add_chat_message("user", "buy 1 AAPL", None)
    stored = db.add_chat_message("assistant", "Done", actions)
    messages = db.get_chat_messages()
    assert [m["role"] for m in messages] == ["user", "assistant"]
    assert messages[0]["actions"] is None
    assert messages[1] == stored
    assert messages[1]["actions"] == actions


def test_chat_messages_limit_keeps_latest():
    for i in range(5):
        db.add_chat_message("user", f"m{i}", None)
    assert [m["content"] for m in db.get_chat_messages(limit=2)] == ["m3", "m4"]
