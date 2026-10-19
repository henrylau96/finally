from app.market.cache import PriceCache

KEYS = {"ticker", "price", "previous_price", "timestamp", "direction", "day_change_pct"}


def test_first_update_is_flat():
    """First update has no previous price and no change."""
    u = PriceCache().update("AAPL", 190.0)
    assert u.direction == "flat"
    assert u.previous_price == u.price
    assert u.day_change_pct == 0.0


def test_direction_up_and_down():
    """Direction follows the move against the prior price."""
    cache = PriceCache()
    cache.update("AAPL", 100.0)
    up = cache.update("AAPL", 101.0)
    down = cache.update("AAPL", 100.5)
    assert (up.direction, up.previous_price) == ("up", 100.0)
    assert (down.direction, down.previous_price) == ("down", 101.0)


def test_day_change_against_session_open():
    """Day change is measured from the first price seen."""
    cache = PriceCache()
    cache.update("AAPL", 100.0)
    assert cache.update("AAPL", 101.5).day_change_pct == 1.5
    assert cache.update("AAPL", 99.0).day_change_pct == -1.0


def test_price_rounded_and_version_bumps():
    """Prices round to 2 dp; version bumps on update and remove."""
    cache = PriceCache()
    v0 = cache.version
    assert cache.update("AAPL", 190.123).price == 190.12
    assert cache.version == v0 + 1
    cache.remove("AAPL")
    assert cache.version == v0 + 2
    assert "AAPL" not in cache.get_all()


def test_to_dict_keys():
    """to_dict exposes exactly the locked six keys."""
    assert set(PriceCache().update("AAPL", 1.0).to_dict()) == KEYS
