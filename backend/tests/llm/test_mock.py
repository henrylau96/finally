"""Tests for the deterministic mock LLM."""

from app.llm.mock import mock_response


def test_buy_parsed():
    r = mock_response("buy 10 AAPL")
    assert [(t.side, t.quantity, t.ticker) for t in r.trades] == [("buy", 10.0, "AAPL")]
    assert r.watchlist_changes == []
    assert r.message == "Mock response: buy 10 AAPL"


def test_sell_case_insensitive_fractional():
    r = mock_response("Please SELL 2.5 msft now")
    assert [(t.side, t.quantity, t.ticker) for t in r.trades] == [("sell", 2.5, "MSFT")]
    assert r.message == "Mock response: sell 2.5 MSFT"


def test_watchlist_add_remove():
    r = mock_response("add pypl and Remove TSLA")
    assert [(c.action, c.ticker) for c in r.watchlist_changes] == [
        ("add", "PYPL"), ("remove", "TSLA")
    ]
    assert r.trades == []
    assert r.message == "Mock response: add PYPL, remove TSLA"


def test_no_actions():
    r = mock_response("How is my portfolio doing?")
    assert r.trades == [] and r.watchlist_changes == []
    assert r.message == "Mock response: no actions"
