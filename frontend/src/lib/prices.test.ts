import { describe, expect, it } from "vitest";
import { applyBatch, emptyPriceState, sessionChange, toChartPoints } from "./prices";
import type { PriceUpdate } from "./types";

const tick = (price: number, timestamp: number): PriceUpdate => ({
  ticker: "AAPL", price, previous_price: price, timestamp, change: 0, change_percent: 0, direction: "flat",
});

describe("applyBatch", () => {
  it("records the first price as session open and accumulates history", () => {
    let s = applyBatch(emptyPriceState, { AAPL: tick(100, 1) });
    s = applyBatch(s, { AAPL: tick(102, 2) });
    expect(s.open.AAPL).toBe(100);
    expect(s.prices.AAPL.price).toBe(102);
    expect(s.history.AAPL).toEqual([{ time: 1, value: 100 }, { time: 2, value: 102 }]);
  });

  it("ignores repeated updates with the same timestamp", () => {
    let s = applyBatch(emptyPriceState, { AAPL: tick(100, 1) });
    s = applyBatch(s, { AAPL: tick(100, 1) });
    expect(s.history.AAPL).toHaveLength(1);
  });
});

describe("sessionChange", () => {
  it("computes percent vs open", () => {
    expect(sessionChange(110, 100)).toBeCloseTo(10);
    expect(sessionChange(110, undefined)).toBe(0);
  });
});

describe("toChartPoints", () => {
  it("floors times and keeps the last value per second", () => {
    const pts = toChartPoints([{ time: 1.2, value: 1 }, { time: 1.7, value: 2 }, { time: 2.1, value: 3 }]);
    expect(pts).toEqual([{ time: 1, value: 2 }, { time: 2, value: 3 }]);
  });
});
