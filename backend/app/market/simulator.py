"""Correlated geometric Brownian motion price engine (pure, synchronous)."""

import math
import random

import numpy as np

from app.market.seed_prices import (
    CORRELATION_GROUPS,
    CROSS_GROUP_CORR,
    DEFAULT_PARAMS,
    INTRA_FINANCE_CORR,
    INTRA_TECH_CORR,
    SEED_PRICES,
    TICKER_PARAMS,
    TSLA_CORR,
)


def _pair_correlation(a: str, b: str) -> float:
    """Correlation between two distinct tickers from the sector rules."""
    if "TSLA" in (a, b):
        return TSLA_CORR
    if a in CORRELATION_GROUPS["tech"] and b in CORRELATION_GROUPS["tech"]:
        return INTRA_TECH_CORR
    if a in CORRELATION_GROUPS["finance"] and b in CORRELATION_GROUPS["finance"]:
        return INTRA_FINANCE_CORR
    return CROSS_GROUP_CORR


class GBMSimulator:
    """Advances correlated prices one tick at a time with random shock events."""

    DEFAULT_DT = 0.5 / (252 * 6.5 * 3600)

    def __init__(
        self,
        tickers: list[str],
        dt: float = DEFAULT_DT,
        event_probability: float = 0.001,
        seed: int | None = None,
    ) -> None:
        self._dt = dt
        self._event_prob = event_probability
        self._rng = np.random.default_rng(seed)
        self._py_rng = random.Random(seed)
        self._tickers: list[str] = []
        self._prices: dict[str, float] = {}
        self._cholesky: np.ndarray | None = None
        for t in tickers:
            self._insert(t)
        self._rebuild_cholesky()

    @property
    def tickers(self) -> list[str]:
        return list(self._tickers)

    def get_price(self, ticker: str) -> float:
        return round(self._prices[ticker], 2)

    def add_ticker(self, ticker: str) -> None:
        """Start simulating a ticker; no-op if already present."""
        if ticker in self._prices:
            return
        self._insert(ticker)
        self._rebuild_cholesky()

    def remove_ticker(self, ticker: str) -> None:
        """Stop simulating a ticker; no-op if absent."""
        if ticker not in self._prices:
            return
        self._tickers.remove(ticker)
        del self._prices[ticker]
        self._rebuild_cholesky()

    def step(self) -> dict[str, float]:
        """Advance all tickers one tick and return rounded prices."""
        z = self._rng.standard_normal(len(self._tickers))
        if self._cholesky is not None:
            z = self._cholesky @ z
        for i, t in enumerate(self._tickers):
            p = TICKER_PARAMS.get(t, DEFAULT_PARAMS)
            drift = (p["mu"] - 0.5 * p["sigma"] ** 2) * self._dt
            self._prices[t] *= math.exp(drift + p["sigma"] * math.sqrt(self._dt) * z[i])
            if self._event_prob > 0 and self._py_rng.random() < self._event_prob:
                self._prices[t] *= 1 + self._py_rng.uniform(0.02, 0.05) * self._py_rng.choice([-1, 1])
        return {t: round(p, 2) for t, p in self._prices.items()}

    def _insert(self, ticker: str) -> None:
        self._tickers.append(ticker)
        self._prices[ticker] = SEED_PRICES.get(ticker) or self._py_rng.uniform(50, 300)

    def _rebuild_cholesky(self) -> None:
        n = len(self._tickers)
        if n < 2:
            self._cholesky = None
            return
        corr = np.eye(n)
        for i in range(n):
            for j in range(i + 1, n):
                corr[i, j] = corr[j, i] = _pair_correlation(self._tickers[i], self._tickers[j])
        self._cholesky = np.linalg.cholesky(corr)
