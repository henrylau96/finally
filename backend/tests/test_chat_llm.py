"""llm.complete: call arguments and structured parsing."""

import os

import litellm

from app.chat import llm
from app.chat.schema import ChatResponse

VALID = (
    '{"message":"ok","trades":[{"ticker":"AAPL","side":"buy","quantity":2}],'
    '"watchlist_changes":[{"ticker":"PYPL","action":"add"}]}'
)


async def test_complete_parses_and_passes_skill_args(llm_reply):
    calls = llm_reply(content=VALID)
    resp = await llm.complete([{"role": "user", "content": "hi"}])
    assert resp.message == "ok"
    assert resp.trades[0].ticker == "AAPL"
    assert resp.watchlist_changes[0].action == "add"
    [kw] = calls
    assert kw["model"] == "openrouter/openai/gpt-oss-120b"
    assert kw["extra_body"] == {"provider": {"order": ["cerebras"]}}
    assert kw["reasoning_effort"] == "low"
    assert kw["response_format"] is ChatResponse
    assert kw["timeout"] == 30


def test_litellm_offline_settings():
    assert os.environ["LITELLM_LOCAL_MODEL_COST_MAP"] == "True"
    assert litellm.suppress_debug_info is True
