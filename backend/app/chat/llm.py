"""LiteLLM -> OpenRouter -> Cerebras structured-output call; the only acompletion call site."""

import os

os.environ.setdefault("LITELLM_LOCAL_MODEL_COST_MAP", "True")

import litellm  # noqa: E402
from litellm import acompletion  # noqa: E402

from app.chat.schema import ChatResponse  # noqa: E402

litellm.suppress_debug_info = True

MODEL = "openrouter/openai/gpt-oss-120b"
EXTRA_BODY = {"provider": {"order": ["cerebras"]}}
TIMEOUT = 30


async def complete(messages: list[dict]) -> ChatResponse:
    """Call the model and parse its reply; raises on provider errors or invalid JSON."""
    response = await acompletion(
        model=MODEL,
        messages=messages,
        response_format=ChatResponse,
        reasoning_effort="low",
        extra_body=EXTRA_BODY,
        timeout=TIMEOUT,
    )
    return ChatResponse.model_validate_json(response.choices[0].message.content or "")
