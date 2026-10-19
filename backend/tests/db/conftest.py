"""Fixtures for database tests."""

import pytest

from app import db


@pytest.fixture(autouse=True)
def tmp_db(tmp_path, monkeypatch):
    """Point DB_PATH at a fresh, initialized temp database."""
    path = tmp_path / "sub" / "test.db"
    monkeypatch.setenv("DB_PATH", str(path))
    db.init_db()
    return path
