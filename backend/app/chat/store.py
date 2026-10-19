"""chat_messages persistence (sync; callers use asyncio.to_thread)."""

import json
from contextlib import closing
from datetime import UTC, datetime
from uuid import uuid4

from app.db import connect, db_path

INSERT = (
    "INSERT INTO chat_messages (id, user_id, role, content, actions, created_at) "
    "VALUES (?, 'default', ?, ?, ?, ?)"
)


def save_turn(user_text: str, user_at: str, assistant_text: str, actions: list[dict]) -> dict:
    """Store the user message and assistant reply together; return the assistant row."""
    row = {
        "id": str(uuid4()),
        "role": "assistant",
        "content": assistant_text,
        "actions": actions,
        "created_at": datetime.now(UTC).isoformat(),
    }
    with closing(connect(db_path())) as conn, conn:
        conn.execute(INSERT, (str(uuid4()), "user", user_text, None, user_at))
        conn.execute(
            INSERT,
            (row["id"], "assistant", assistant_text, json.dumps(actions), row["created_at"]),
        )
    return row


def history(limit: int = 50) -> list[dict]:
    """Return the most recent messages, oldest first, with actions parsed."""
    with closing(connect(db_path())) as conn:
        rows = conn.execute(
            "SELECT id, role, content, actions, created_at FROM ("
            "SELECT rowid AS r, id, role, content, actions, created_at FROM chat_messages "
            "WHERE user_id = 'default' ORDER BY rowid DESC LIMIT ?) ORDER BY r",
            (limit,),
        ).fetchall()
    return [
        {
            "id": r["id"],
            "role": r["role"],
            "content": r["content"],
            "actions": None if r["actions"] is None else json.loads(r["actions"]),
            "created_at": r["created_at"],
        }
        for r in rows
    ]
