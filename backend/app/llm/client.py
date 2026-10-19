"""LLM call via LiteLLM -> OpenRouter -> Cerebras with structured outputs."""

import logging

from pydantic import ValidationError

from .schema import ChatResponse

logger = logging.getLogger(__name__)

MODEL = "openrouter/openai/gpt-oss-120b"
EXTRA_BODY = {"provider": {"order": ["cerebras"]}}
FALLBACK_MESSAGE = "Sorry, I could not understand the AI response. Please try again."


def parse_response(content: str | None) -> ChatResponse:
    """Parse the LLM's JSON content, falling back to a friendly message with no actions."""
    try:
        return ChatResponse.model_validate_json(content or "")
    except ValidationError:
        logger.warning("Malformed LLM response: %r", content)
        return ChatResponse(message=FALLBACK_MESSAGE)


async def call_llm(messages: list[dict]) -> ChatResponse:
    """Call the model with structured output and return the parsed response."""
    from litellm import acompletion  # imported lazily: litellm is slow to import

    response = await acompletion(
        model=MODEL,
        messages=messages,
        response_format=ChatResponse,
        reasoning_effort="low",
        extra_body=EXTRA_BODY,
    )
    return parse_response(response.choices[0].message.content)
