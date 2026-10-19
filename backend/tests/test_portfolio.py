from contextlib import closing

import pytest

from app import db
from app.market.cache import PriceCache
from app.portfolio import TradeError, execute_trade, portfolio_view


@pytest.fixture(autouse=True)
def fresh(db_env):
    db.init_db()


def count(table, where="1=1"):
    with closing(db.connect(db.db_path())) as conn:
        return conn.execute(f"SELECT COUNT(*) FROM {table} WHERE {where}").fetchone()[0]


def cash():
    with closing(db.connect(db.db_path())) as conn:
        return conn.execute("SELECT cash_balance FROM users_profile").fetchone()[0]


def test_buy_new_position():
    r = execute_trade("AAPL", "buy", 2, 100.0)
    assert r["cash_balance"] == 9800.0
    assert r["position"] == {"ticker": "AAPL", "quantity": 2, "avg_cost": 100.0}
    t = r["trade"]
    assert t["id"] and t["side"] == "buy" and t["quantity"] == 2 and t["price"] == 100.0
    assert t["executed_at"]


def test_avg_cost_weighted():
    execute_trade("AAPL", "buy", 2, 100.0)
    r = execute_trade("AAPL", "buy", 2, 110.0)
    assert r["position"]["quantity"] == 4 and r["position"]["avg_cost"] == 105.0
    assert count("positions") == 1


def test_fractional():
    r = execute_trade("AAPL", "buy", 0.5, 190.42)
    assert r["position"]["quantity"] == 0.5
    assert r["cash_balance"] == round(10000 - round(0.5 * 190.42, 2), 2)
    r = execute_trade("MSFT", "buy", 1.2999999999999998, 10.0)
    assert r["position"]["quantity"] == 1.3


def test_partial_sell_keeps_avg():
    execute_trade("AAPL", "buy", 3, 100.0)
    r = execute_trade("AAPL", "sell", 1, 120.0)
    assert r["position"]["quantity"] == 2 and r["position"]["avg_cost"] == 100.0
    assert r["cash_balance"] == 10000 - 300 + 120


def test_sell_all_deletes():
    execute_trade("AAPL", "buy", 2.3, 100.0)
    execute_trade("AAPL", "sell", 1.2999999999999998, 100.0)
    r = execute_trade("AAPL", "sell", 1, 100.0)
    assert r["position"] is None
    assert count("positions", "ticker = 'AAPL'") == 0


def test_sell_at_loss():
    execute_trade("AAPL", "buy", 10, 100.0)
    r = execute_trade("AAPL", "sell", 10, 80.0)
    assert r["cash_balance"] == 9800.0 and r["position"] is None


def test_insufficient_cash():
    with pytest.raises(TradeError, match=r"^Insufficient cash: need \$10,100.00, have \$10,000.00"):
        execute_trade("AAPL", "buy", 101, 100.0)
    assert cash() == 10000.0 and count("positions") == 0 and count("trades") == 0


def test_oversell(seed_position):
    seed_position("AAPL", 2, 100.0)
    with pytest.raises(TradeError, match="^Cannot sell 3 AAPL; you hold 2$"):
        execute_trade("AAPL", "sell", 3, 100.0)
    with pytest.raises(TradeError, match="you hold 0$"):
        execute_trade("MSFT", "sell", 1, 100.0)
    assert cash() == 10000.0 and count("trades") == 0


def test_trade_log():
    execute_trade("AAPL", "buy", 1, 100.0)
    execute_trade("AAPL", "sell", 1, 100.0)
    with pytest.raises(TradeError):
        execute_trade("AAPL", "sell", 1, 100.0)
    assert count("trades") == 2


def test_portfolio_view(seed_position):
    seed_position("AAPL", 2, 100.0)
    seed_position("ZZZZ", 1, 50.0)
    cache = PriceCache()
    cache.update("AAPL", 110.0)
    v = portfolio_view(cache)
    aapl, zzzz = v["positions"]
    assert (aapl["current_price"], aapl["market_value"], aapl["unrealized_pnl"], aapl["pnl_pct"]) == (
        110.0, 220.0, 20.0, 10.0,
    )
    assert zzzz["current_price"] == 50.0 and zzzz["unrealized_pnl"] == 0.0
    assert v["total_value"] == 10000.0 + 270.0
    assert v["unrealized_pnl"] == 20.0


def test_micro_buys_pay_full_value():
    """Repeated tiny fills cost exactly price x quantity; a round trip creates no money."""
    for _ in range(100):
        execute_trade("ZZZ", "buy", 0.0001, 49.99)
    assert cash() == pytest.approx(10000 - 0.01 * 49.99)
    execute_trade("ZZZ", "sell", 0.01, 49.99)
    assert cash() == pytest.approx(10000.0)


def test_portfolio_view_consistent_read(monkeypatch):
    """A trade committing between the cash and positions reads must not tear the total."""
    from app import portfolio

    real_connect = portfolio.connect

    class TradeMidRead:
        def __init__(self, conn):
            self.conn = conn

        def __getattr__(self, name):
            return getattr(self.conn, name)

        def execute(self, sql, *args):
            if "FROM positions" in sql:
                with closing(real_connect(db.db_path())) as other, other:
                    other.execute("UPDATE users_profile SET cash_balance = 9000.0")
                    other.execute(
                        "INSERT INTO positions (id, user_id, ticker, quantity, avg_cost, updated_at) "
                        "VALUES ('p', 'default', 'AAPL', 10, 100.0, 'now')"
                    )
            return self.conn.execute(sql, *args)

    monkeypatch.setattr(portfolio, "connect", lambda path: TradeMidRead(real_connect(path)))
    assert portfolio_view(PriceCache())["total_value"] == 10000.0
