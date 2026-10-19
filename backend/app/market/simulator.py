"""Geometric Brownian motion price engine (pure, synchronous)."""

import math
import random

import numpy as np

from app.market.seed_prices import DEFAULT_PARAMS, SEED_PRICES, TICKER_PARAMS


class GBMSimulator:
    """Advances prices one tick at a time with optional random shock events."""

    DEFAULT_DT = 0.5 / (252 * 6.5 * 3600)

    def __init__(
        self,
        tickers: list[str],
        dt: float = DEFAULT_DT,
        event_probability: float = 0.0,
        seed: int | None = None,
    ) -> None:
        self._dt = dt
        self._event_prob = event_probability
        self._rng = np.random.default_rng(seed)
        self._py_rng = random.Random(seed)
        self._tickers = list(tickers)
        self._prices = {t: SEED_PRICES[t] for t in self._tickers}

    @property
    def tickers(self) -> list[str]:
        return list(self._tickers)

    def get_price(self, ticker: str) -> float:
        return round(self._prices[ticker], 2)

    def step(self) -> dict[str, float]:
        """Advance all tickers one tick and return rounded prices."""
        z = self._rng.standard_normal(len(self._tickers))
        for i, t in enumerate(self._tickers):
            p = TICKER_PARAMS.get(t, DEFAULT_PARAMS)
            drift = (p["mu"] - 0.5 * p["sigma"] ** 2) * self._dt
            self._prices[t] *= math.exp(drift + p["sigma"] * math.sqrt(self._dt) * z[i])
            if self._event_prob > 0 and self._py_rng.random() < self._event_prob:
                self._prices[t] *= 1 + self._py_rng.uniform(0.02, 0.05) * self._py_rng.choice([-1, 1])
        return {t: round(p, 2) for t, p in self._prices.items()}
