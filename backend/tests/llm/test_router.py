"""Tests for the chat HTTP routes."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.llm import create_chat_router


@pytest.fixture
def client(monkeypatch, cache, source):
    monkeypatch.setenv("LLM_MOCK", "true")
    app = FastAPI()
    app.include_router(create_chat_router(cache, source))
    return TestClient(app)


def test_post_chat_and_history(client):
    r = client.post("/api/chat", json={"message": "buy 1 AAPL"})
    assert r.status_code == 200
    assert r.json()["trades"][0]["status"] == "executed"

    history = client.get("/api/chat/history").json()
    assert [m["role"] for m in history] == ["user", "assistant"]
    assert set(history[0]) == {"id", "role", "content", "actions", "created_at"}


def test_empty_message_rejected(client):
    assert client.post("/api/chat", json={"message": ""}).status_code == 422
