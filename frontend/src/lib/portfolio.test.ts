import { describe, expect, it } from "vitest";
import { derivePositions, pnlState, toSeries, type Portfolio } from "./portfolio";
import type { Quote } from "./usePriceStream";

const pos = (ticker: string, quantity: number, avg_cost: number, current_price: number) => ({
  ticker,
  quantity,
  avg_cost,
  current_price,
  market_value: current_price * quantity,
  unrealized_pnl: 0,
  pnl_pct: 0,
});

const portfolio: Portfolio = {
  cash_balance: 1000,
  total_value: 0,
  unrealized_pnl: 0,
  positions: [pos("AAPL", 10, 100, 110), pos("MSFT", 2, 400, 400)],
};

const quote = (price: number) => ({ price }) as Quote;

describe("derivePositions", () => {
  it("returns unset values before the portfolio loads", () => {
    expect(derivePositions(null, {})).toEqual({ rows: null, total: undefined });
  });

  it("marks positions to live quotes and totals with cash", () => {
    const { rows, total } = derivePositions(portfolio, { AAPL: quote(120) });
    const aapl = rows!.find((r) => r.ticker === "AAPL")!;
    expect(aapl.unrealized_pnl).toBeCloseTo(200);
    expect(aapl.pnl_pct).toBeCloseTo(20);
    expect(total).toBeCloseTo(1000 + 1200 + 800);
  });

  it("keeps fetched market value order even when live prices would reorder", () => {
    const { rows } = derivePositions(portfolio, { AAPL: quote(10) });
    expect(rows!.map((r) => r.ticker)).toEqual(["AAPL", "MSFT"]);
  });

  it("falls back to current_price without a quote", () => {
    const { rows } = derivePositions(portfolio, {});
    expect(rows![0].current_price).toBe(110);
  });
});

describe("pnlState", () => {
  it("classifies by rounded display value", () => {
    expect(pnlState(0.004)).toBe("flat");
    expect(pnlState(1.5)).toBe("positive");
    expect(pnlState(-0.5)).toBe("negative");
  });
});

describe("toSeries", () => {
  it("keeps the last value per second and skips out-of-order snapshots", () => {
    const series = toSeries([
      { total_value: 1, recorded_at: "2026-01-01T00:00:10.100Z" },
      { total_value: 2, recorded_at: "2026-01-01T00:00:10.900Z" },
      { total_value: 3, recorded_at: "2026-01-01T00:00:05Z" },
      { total_value: 4, recorded_at: "2026-01-01T00:00:12Z" },
    ]);
    expect(series.map((s) => s.value)).toEqual([2, 4]);
    expect(series[0].time).toBeLessThan(series[1].time);
  });
});
