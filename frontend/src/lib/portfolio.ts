import type { Portfolio, Position, PriceUpdate } from "./types";

export type PnlSign = "positive" | "negative" | "flat";

/** Re-price a position with the latest streamed price, if one exists. */
export function revaluePosition(pos: Position, live?: PriceUpdate): Position {
  const current = live?.price ?? pos.current_price;
  const marketValue = pos.quantity * current;
  const cost = pos.quantity * pos.avg_cost;
  const pnl = marketValue - cost;
  return {
    ...pos,
    current_price: current,
    market_value: marketValue,
    unrealized_pnl: pnl,
    unrealized_pnl_percent: cost ? (pnl / cost) * 100 : 0,
  };
}

/** Re-price the whole portfolio from live prices so totals update between fetches. */
export function revaluePortfolio(
  portfolio: Portfolio,
  prices: Record<string, PriceUpdate>,
): Portfolio {
  const positions = portfolio.positions.map((p) => revaluePosition(p, prices[p.ticker]));
  const invested = positions.reduce((sum, p) => sum + p.market_value, 0);
  const pnl = positions.reduce((sum, p) => sum + p.unrealized_pnl, 0);
  return {
    ...portfolio,
    positions,
    total_value: portfolio.cash_balance + invested,
    total_unrealized_pnl: pnl,
  };
}

/** Classify a P&L amount, treating sub-cent values as flat. */
export function pnlSign(pnl: number): PnlSign {
  if (pnl > 0.005) return "positive";
  if (pnl < -0.005) return "negative";
  return "flat";
}
