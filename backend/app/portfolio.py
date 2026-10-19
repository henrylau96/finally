"""Atomic market-order execution and the portfolio view."""

from contextlib import closing
from datetime import UTC, datetime
from uuid import uuid4

from app.db import connect, db_path
from app.market.cache import PriceCache

EPS = 1e-9


class TradeError(Exception):
    """A trade rejected by validation; the message is shown to the user."""


def _next_position(side, held, avg, quantity, price):
    """Return (new_qty, new_avg_cost) after applying a fill."""
    if side == "sell":
        return round(held - quantity, 4), avg
    new_qty = round(held + quantity, 4)
    if held <= EPS:
        return new_qty, price
    return new_qty, round((held * avg + quantity * price) / new_qty, 4)


def _validate(side, ticker, quantity, amount, cash, held):
    if side == "buy" and amount > cash + EPS:
        raise TradeError(f"Insufficient cash: need ${amount:,.2f}, have ${cash:,.2f}")
    if side == "sell" and quantity > held + EPS:
        raise TradeError(f"Cannot sell {quantity:g} {ticker}; you hold {held:g}")


def _write(conn, ticker, side, quantity, price, new_cash, new_qty, new_avg, now):
    conn.execute("UPDATE users_profile SET cash_balance = ? WHERE id = 'default'", (new_cash,))
    if new_qty <= EPS:
        conn.execute("DELETE FROM positions WHERE user_id = 'default' AND ticker = ?", (ticker,))
    else:
        conn.execute(
            "INSERT INTO positions (id, user_id, ticker, quantity, avg_cost, updated_at) "
            "VALUES (?, 'default', ?, ?, ?, ?) "
            "ON CONFLICT(user_id, ticker) DO UPDATE SET quantity=excluded.quantity, "
            "avg_cost=excluded.avg_cost, updated_at=excluded.updated_at",
            (str(uuid4()), ticker, new_qty, new_avg, now),
        )
    trade_id = str(uuid4())
    conn.execute(
        "INSERT INTO trades (id, user_id, ticker, side, quantity, price, executed_at) "
        "VALUES (?, 'default', ?, ?, ?, ?, ?)",
        (trade_id, ticker, side, quantity, price, now),
    )
    return trade_id


def execute_trade(ticker: str, side: str, quantity: float, price: float) -> dict:
    """Fill a market order in one transaction; raise TradeError and change nothing on rejection."""
    quantity = round(quantity, 4)
    amount = round(quantity * price, 2)
    now = datetime.now(UTC).isoformat()
    with closing(connect(db_path())) as conn:
        conn.execute("BEGIN IMMEDIATE")
        try:
            cash = conn.execute("SELECT cash_balance FROM users_profile WHERE id = 'default'").fetchone()[0]
            pos = conn.execute(
                "SELECT quantity, avg_cost FROM positions WHERE user_id = 'default' AND ticker = ?",
                (ticker,),
            ).fetchone()
            held, avg = (pos["quantity"], pos["avg_cost"]) if pos else (0.0, 0.0)
            _validate(side, ticker, quantity, amount, cash, held)
            new_cash = round(cash - amount if side == "buy" else cash + amount, 2)
            new_qty, new_avg = _next_position(side, held, avg, quantity, price)
            trade_id = _write(conn, ticker, side, quantity, price, new_cash, new_qty, new_avg, now)
            conn.commit()
        except BaseException:
            conn.rollback()
            raise
    position = None if new_qty <= EPS else {"ticker": ticker, "quantity": new_qty, "avg_cost": new_avg}
    trade = {"id": trade_id, "ticker": ticker, "side": side, "quantity": quantity,
             "price": price, "executed_at": now}
    return {"trade": trade, "cash_balance": new_cash, "position": position}


def portfolio_view(cache: PriceCache) -> dict:
    """Return cash, positions marked to the cached price (avg cost fallback), totals and P&L."""
    with closing(connect(db_path())) as conn:
        cash = conn.execute("SELECT cash_balance FROM users_profile WHERE id = 'default'").fetchone()[0]
        rows = conn.execute(
            "SELECT ticker, quantity, avg_cost FROM positions WHERE user_id = 'default' ORDER BY rowid"
        ).fetchall()
    positions = []
    for r in rows:
        u = cache.get(r["ticker"])
        price = u.price if u else r["avg_cost"]
        positions.append({
            "ticker": r["ticker"],
            "quantity": r["quantity"],
            "avg_cost": r["avg_cost"],
            "current_price": price,
            "market_value": round(r["quantity"] * price, 2),
            "unrealized_pnl": round((price - r["avg_cost"]) * r["quantity"], 2),
            "pnl_pct": round((price - r["avg_cost"]) / r["avg_cost"] * 100, 2),
        })
    return {
        "cash_balance": cash,
        "total_value": round(cash + sum(p["market_value"] for p in positions), 2),
        "unrealized_pnl": round(sum(p["unrealized_pnl"] for p in positions), 2),
        "positions": positions,
    }
