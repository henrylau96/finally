"""Prompt assembly: system prompt, live portfolio block, history, user text."""

from app import db
from app.market.cache import PriceCache
from app.portfolio import portfolio_view

SYSTEM_PROMPT = """You are FinAlly, an AI trading assistant inside a simulated trading workstation.
- Analyze portfolio composition, risk concentration and P&L.
- Suggest trades with brief reasoning.
- Execute trades only when the user asks or agrees; leave trades empty when only advising.
- Manage the watchlist proactively.
- Be concise and data-driven.
- Quantities are share counts. Tickers are uppercase 1-5 letter real US symbols.
- Always reply with JSON: {"message": str, "trades": [{"ticker", "side": "buy"|"sell", "quantity"}], \
"watchlist_changes": [{"ticker", "action": "add"|"remove"}]}."""


def portfolio_context(cache: PriceCache) -> str:
    """Return a compact text snapshot of cash, positions and watchlist with live prices."""
    view = portfolio_view(cache)
    lines = [
        f"Cash: ${view['cash_balance']:,.2f}",
        f"Total value: ${view['total_value']:,.2f}",
        f"Unrealized P&L: ${view['unrealized_pnl']:,.2f}",
        "Positions:",
    ]
    for p in view["positions"]:
        lines.append(
            f"- {p['ticker']}: {p['quantity']:g} sh, avg cost {p['avg_cost']:.2f}, price {p['current_price']:.2f}, "
            f"P&L ${p['unrealized_pnl']:,.2f} ({p['pnl_pct']:+.2f}%)"
        )
    if not view["positions"]:
        lines.append("- none")
    lines.append("Watchlist:")
    for row in db.list_watchlist():
        u = cache.get(row["ticker"])
        lines.append(
            f"- {row['ticker']}: {u.price:.2f} ({u.day_change_pct:+.2f}% day)" if u else f"- {row['ticker']}: no price"
        )
    return "\n".join(lines)


def _action_text(a: dict) -> str:
    if a["type"] == "trade":
        verb = {"buy": "bought", "sell": "sold"}[a["side"]]
        if a["ok"]:
            return f"{verb} {a['quantity']:g} {a['ticker']} @ {a['price']:.2f}"
        return f"failed: {a['side']} {a['quantity']:g} {a['ticker']} - {a.get('error')}"
    if a["ok"]:
        return f"{'added' if a['action'] == 'add' else 'removed'} {a['ticker']}"
    return f"failed: {a['action']} {a['ticker']} - {a.get('error')}"


def build_messages(context: str, history: list[dict], text: str) -> list[dict]:
    """Return the chat messages: system prompt, portfolio block, history oldest-first, user text."""
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "system", "content": "Current portfolio state (live):\n" + context},
    ]
    for h in history:
        content = h["content"]
        if h.get("actions"):
            content += " [actions: " + "; ".join(_action_text(a) for a in h["actions"]) + "]"
        messages.append({"role": h["role"], "content": content})
    messages.append({"role": "user", "content": text})
    return messages
