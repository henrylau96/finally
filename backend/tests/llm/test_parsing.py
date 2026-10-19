"""Tests for structured output parsing and the LLM call."""

import json
import sys
from types import ModuleType, SimpleNamespace

from app.llm.client import FALLBACK_MESSAGE, MODEL, call_llm, parse_response
from app.llm.schema import ChatResponse


def test_full_response():
    content = json.dumps({
        "message": "Done",
        "trades": [{"ticker": "AAPL", "side": "buy", "quantity": 5}],
        "watchlist_changes": [{"ticker": "PYPL", "action": "add"}],
    })
    r = parse_response(content)
    assert r.message == "Done"
    assert r.trades[0].ticker == "AAPL" and r.trades[0].quantity == 5
    assert r.watchlist_changes[0].action == "add"


def test_missing_optional_fields():
    r = parse_response('{"message": "Hi"}')
    assert r.message == "Hi" and r.trades == [] and r.watchlist_changes == []


def test_malformed_json():
    r = parse_response("not json {")
    assert r.message == FALLBACK_MESSAGE and r.trades == []


def test_invalid_schema():
    r = parse_response('{"message": "x", "trades": [{"ticker": "AAPL", "side": "hold"}]}')
    assert r.message == FALLBACK_MESSAGE and r.trades == []


def test_empty_content():
    assert parse_response(None).message == FALLBACK_MESSAGE


async def test_call_llm_uses_structured_output(monkeypatch):
    calls = {}

    async def fake_acompletion(**kwargs):
        calls.update(kwargs)
        message = SimpleNamespace(content='{"message": "ok", "trades": [], "watchlist_changes": []}')
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])

    fake = ModuleType("litellm")
    fake.acompletion = fake_acompletion
    monkeypatch.setitem(sys.modules, "litellm", fake)

    r = await call_llm([{"role": "user", "content": "hi"}])
    assert r.message == "ok"
    assert calls["model"] == MODEL
    assert calls["response_format"] is ChatResponse
    assert calls["extra_body"] == {"provider": {"order": ["cerebras"]}}
