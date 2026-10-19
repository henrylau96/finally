"""Trade execution and portfolio valuation."""

from __future__ import annotations

import sqlite3

from app import db
from app.market import PriceCache

EPSILON = 1e-9


class TradeError(Exception):
    """A trade failed validation. The message is user-facing."""


def execute_trade(
    ticker: str, side: str, quantity: float, price_cache: PriceCache, user_id: str = "default"
) -> dict:
    """Execute a market order at the current cached price and return the trade row."""
    ticker = ticker.upper().strip()
    side = side.lower().strip()
    if side not in ("buy", "sell"):
        raise TradeError(f"Invalid side '{side}': must be 'buy' or 'sell'")
    if quantity <= 0:
        raise TradeError("Quantity must be greater than 0")
    price = price_cache.get_price(ticker)
    if price is None:
        raise TradeError(f"No price available for {ticker}")

    with db.transaction() as conn:
        if side == "buy":
            _buy(ticker, quantity, price, user_id, conn)
        else:
            _sell(ticker, quantity, price, user_id, conn)
        trade = db.record_trade(ticker, side, quantity, price, user_id, conn=conn)
        total = get_portfolio(price_cache, user_id, conn)["total_value"]
        db.record_snapshot(total, user_id, conn=conn)
    return trade


def _buy(ticker: str, quantity: float, price: float, user_id: str, conn: sqlite3.Connection):
    cash = db.get_cash(user_id, conn=conn)
    cost = quantity * price
    if cost > cash + EPSILON:
        raise TradeError(f"Insufficient cash: need ${cost:,.2f}, have ${cash:,.2f}")
    position = db.get_position(ticker, user_id, conn=conn)
    old_qty = position["quantity"] if position else 0.0
    old_cost = position["avg_cost"] if position else 0.0
    new_qty = old_qty + quantity
    avg_cost = (old_qty * old_cost + quantity * price) / new_qty
    db.set_cash(cash - cost, user_id, conn=conn)
    db.upsert_position(ticker, new_qty, avg_cost, user_id, conn=conn)


def _sell(ticker: str, quantity: float, price: float, user_id: str, conn: sqlite3.Connection):
    position = db.get_position(ticker, user_id, conn=conn)
    held = position["quantity"] if position else 0.0
    if quantity > held + EPSILON:
        raise TradeError(f"Insufficient shares: trying to sell {quantity:g} {ticker}, have {held:g}")
    cash = db.get_cash(user_id, conn=conn)
    db.set_cash(cash + quantity * price, user_id, conn=conn)
    remaining = held - quantity
    if remaining <= EPSILON:
        db.delete_position(ticker, user_id, conn=conn)
    else:
        db.upsert_position(ticker, remaining, position["avg_cost"], user_id, conn=conn)


def _position_view(position: dict, price_cache: PriceCache) -> dict:
    qty, avg = position["quantity"], position["avg_cost"]
    price = price_cache.get_price(position["ticker"]) or avg
    pnl = (price - avg) * qty
    cost_basis = avg * qty
    return {
        "ticker": position["ticker"],
        "quantity": qty,
        "avg_cost": round(avg, 4),
        "current_price": price,
        "market_value": round(price * qty, 2),
        "unrealized_pnl": round(pnl, 2),
        "unrealized_pnl_percent": round(pnl / cost_basis * 100, 2) if cost_basis else 0.0,
    }


def get_portfolio(
    price_cache: PriceCache, user_id: str = "default", conn: sqlite3.Connection | None = None
) -> dict:
    """Return cash, positions valued at live prices, total value, and unrealized P&L."""
    cash = db.get_cash(user_id, conn=conn)
    positions = [_position_view(p, price_cache) for p in db.get_positions(user_id, conn=conn)]
    invested = sum((p["market_value"] for p in positions), 0.0)
    return {
        "cash_balance": round(cash, 2),
        "total_value": round(cash + invested, 2),
        "total_unrealized_pnl": round(sum((p["unrealized_pnl"] for p in positions), 0.0), 2),
        "positions": positions,
    }


def total_value(price_cache: PriceCache, user_id: str = "default") -> float:
    """Return cash plus the market value of all positions."""
    return get_portfolio(price_cache, user_id)["total_value"]
