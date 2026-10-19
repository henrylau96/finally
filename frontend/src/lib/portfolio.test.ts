import { describe, expect, it } from "vitest";
import { pnlSign, revaluePortfolio } from "./portfolio";
import type { Portfolio, PriceUpdate } from "./types";

const portfolio: Portfolio = {
  cash_balance: 8000,
  total_value: 10000,
  total_unrealized_pnl: 0,
  positions: [
    { ticker: "AAPL", quantity: 10, avg_cost: 200, current_price: 200, market_value: 2000, unrealized_pnl: 0, unrealized_pnl_percent: 0 },
  ],
};

const tick = (ticker: string, price: number): PriceUpdate => ({
  ticker, price, previous_price: price, timestamp: 0, change: 0, change_percent: 0, direction: "flat",
});

describe("revaluePortfolio", () => {
  it("re-prices positions and totals from live prices", () => {
    const result = revaluePortfolio(portfolio, { AAPL: tick("AAPL", 210) });
    expect(result.total_value).toBe(10100);
    expect(result.total_unrealized_pnl).toBe(100);
    expect(result.positions[0].unrealized_pnl_percent).toBeCloseTo(5);
  });

  it("keeps server prices when no live price exists", () => {
    const result = revaluePortfolio(portfolio, {});
    expect(result.total_value).toBe(10000);
  });
});

describe("pnlSign", () => {
  it("classifies gains, losses and flat", () => {
    expect(pnlSign(5)).toBe("positive");
    expect(pnlSign(-5)).toBe("negative");
    expect(pnlSign(0.001)).toBe("flat");
  });
});
