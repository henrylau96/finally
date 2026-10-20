"""Route-audit gaps: chat validation bodies, chat history shape, unknown API paths."""

import pytest


@pytest.fixture(autouse=True)
def mock_llm(monkeypatch):
    monkeypatch.setenv("LLM_MOCK", "true")


@pytest.mark.parametrize("body", [{"message": ""}, {"message": "   "}, {}, {"message": "x" * 2001}])
async def test_chat_invalid_body_is_422_with_detail(client, body):
    r = await client.post("/api/chat", json=body)
    assert r.status_code == 422
    assert "detail" in r.json()


async def test_chat_history_entry_shape(client):
    await client.post("/api/chat", json={"message": "hello"})
    r = await client.get("/api/chat/history")
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) == 2
    assert all(set(row) == {"id", "role", "content", "actions", "created_at"} for row in rows)


async def test_unknown_api_path_is_404(client):
    assert (await client.get("/api/does-not-exist")).status_code == 404
