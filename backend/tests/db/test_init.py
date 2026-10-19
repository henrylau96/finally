"""Tests for DB path handling, lazy init, seeding, and transactions."""

import sqlite3

import pytest

from app import db


def test_db_path_from_env(tmp_db):
    assert db.get_db_path() == tmp_db
    assert tmp_db.exists()


def test_default_db_path(monkeypatch):
    monkeypatch.delenv("DB_PATH")
    path = db.get_db_path()
    assert path.name == "finally.db"
    assert path.parent.name == "db"
    assert (path.parent.parent / "backend").is_dir()


def test_seed_data():
    assert db.get_cash() == 10000.0
    assert db.get_watchlist() == db.DEFAULT_TICKERS


def test_init_is_idempotent():
    db.set_cash(5000.0)
    db.remove_from_watchlist("AAPL")
    db.init_db()
    assert db.get_cash() == 5000.0
    assert "AAPL" not in db.get_watchlist()
    assert len(db.get_watchlist()) == 9


def test_init_seeds_other_user():
    db.init_db(user_id="alice")
    assert db.get_cash("alice") == 10000.0
    assert db.get_watchlist("alice") == db.DEFAULT_TICKERS


def test_all_tables_created(tmp_db):
    conn = sqlite3.connect(tmp_db)
    names = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    conn.close()
    assert {"users_profile", "watchlist", "positions", "trades",
            "portfolio_snapshots", "chat_messages"} <= names


def test_transaction_commits():
    with db.transaction() as conn:
        db.set_cash(1.0, conn=conn)
        db.record_trade("AAPL", "buy", 1, 190.0, conn=conn)
    assert db.get_cash() == 1.0
    assert len(db.get_trades()) == 1


def test_transaction_holds_write_lock_immediately(tmp_db):
    with db.transaction() as conn:
        assert conn.in_transaction
        other = sqlite3.connect(tmp_db, timeout=0)
        with pytest.raises(sqlite3.OperationalError, match="locked"):
            other.execute("BEGIN IMMEDIATE")
        other.close()


def test_transaction_rolls_back_on_error():
    with pytest.raises(RuntimeError):
        with db.transaction() as conn:
            db.set_cash(1.0, conn=conn)
            db.upsert_position("AAPL", 1, 190.0, conn=conn)
            raise RuntimeError("boom")
    assert db.get_cash() == 10000.0
    assert db.get_positions() == []
