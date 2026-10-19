import type { UTCTimestamp } from "lightweight-charts";
import type { Quote } from "./usePriceStream";

export type Position = {
  ticker: string;
  quantity: number;
  avg_cost: number;
  current_price: number;
  market_value: number;
  unrealized_pnl: number;
  pnl_pct: number;
};

export type Portfolio = {
  cash_balance: number;
  total_value: number;
  unrealized_pnl: number;
  positions: Position[];
};

export type PositionRow = Position;

/**
 * Mark positions to live quotes; rows and total are unset until the portfolio has loaded.
 * Rows are ordered by market value as of the last portfolio fetch, so live ticks never reorder them.
 */
export function derivePositions(
  p: Portfolio | null,
  quotes: Record<string, Quote>,
): { rows: PositionRow[] | null; total: number | undefined } {
  if (!p) return { rows: null, total: undefined };
  const rows = [...p.positions]
    .sort((a, b) => b.market_value - a.market_value)
    .map((pos) => {
      const price = quotes[pos.ticker]?.price ?? pos.current_price ?? pos.avg_cost;
      return {
        ...pos,
        current_price: price,
        market_value: price * pos.quantity,
        unrealized_pnl: (price - pos.avg_cost) * pos.quantity,
        pnl_pct: ((price - pos.avg_cost) / pos.avg_cost) * 100,
      };
    });
  const total = p.cash_balance + rows.reduce((sum, r) => sum + r.market_value, 0);
  return { rows, total };
}

/** Classify a P&L percent by its rounded display value, matching formatPct. */
export function pnlState(pct: number): "positive" | "negative" | "flat" {
  if (Number(Math.abs(pct).toFixed(2)) === 0) return "flat";
  return pct > 0 ? "positive" : "negative";
}

/** ISO snapshots oldest-first to strictly ascending whole seconds; last value wins per second. */
export function toSeries(h: { total_value: number; recorded_at: string }[]) {
  const out: { time: UTCTimestamp; value: number }[] = [];
  for (const s of h) {
    const time = Math.floor(Date.parse(s.recorded_at) / 1000) as UTCTimestamp;
    const last = out[out.length - 1];
    if (last && time < last.time) continue;
    if (last && time === last.time) last.value = s.total_value;
    else out.push({ time, value: s.total_value });
  }
  return out;
}
