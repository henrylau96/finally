"""Prompt construction: system prompt, portfolio context, and history."""

import json

SYSTEM_PROMPT = """You are FinAlly, an AI trading assistant in a simulated trading workstation.
You help the user with their portfolio of simulated money. You can:
- Analyze portfolio composition, risk concentration, and P&L
- Suggest trades with brief reasoning
- Execute trades when the user asks or agrees (market orders, instant fill at current price)
- Manage the watchlist proactively (add or remove tickers)

Be concise and data-driven. Only include trades the user asked for or agreed to.
Always respond with valid JSON matching the schema: a "message" string for the user,
a "trades" list of {ticker, side ("buy"|"sell"), quantity}, and a "watchlist_changes"
list of {ticker, action ("add"|"remove")}. Use empty lists when there are no actions."""


def format_context(portfolio: dict, watchlist: list[dict]) -> str:
    """Render the user's portfolio and watchlist as a context block."""
    return (
        "Live state right now. It already reflects every trade and watchlist change made "
        "earlier in this conversation; use these numbers exactly and never re-apply past "
        "actions.\n\n"
        "Current portfolio (JSON):\n"
        f"{json.dumps(portfolio)}\n\n"
        "Watchlist with live prices (JSON):\n"
        f"{json.dumps(watchlist)}"
    )


def build_messages(
    user_message: str, portfolio: dict, watchlist: list[dict], history: list[dict]
) -> list[dict]:
    """Assemble the chat messages sent to the LLM.

    The live context goes after the history so the model reads it as the state that
    follows all past trades, not as the state before them.
    """
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages += [{"role": m["role"], "content": m["content"]} for m in history]
    messages.append({"role": "system", "content": format_context(portfolio, watchlist)})
    messages.append({"role": "user", "content": user_message})
    return messages
