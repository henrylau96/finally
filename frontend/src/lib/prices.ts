import type { PricePoint, PriceUpdate } from "./types";

export const MAX_POINTS = 600;

export interface PriceState {
  prices: Record<string, PriceUpdate>;
  history: Record<string, PricePoint[]>;
  open: Record<string, number>;
}

export const emptyPriceState: PriceState = { prices: {}, history: {}, open: {} };

/** Merge one SSE batch into state: latest prices, capped history, first-seen price. */
export function applyBatch(state: PriceState, batch: Record<string, PriceUpdate>): PriceState {
  const prices = { ...state.prices };
  const history = { ...state.history };
  const open = { ...state.open };
  for (const [ticker, update] of Object.entries(batch)) {
    const points = history[ticker] ?? [];
    const last = points[points.length - 1];
    if (last && last.time === update.timestamp) continue;
    prices[ticker] = update;
    history[ticker] = [...points, { time: update.timestamp, value: update.price }].slice(-MAX_POINTS);
    open[ticker] ??= update.price;
  }
  return { prices, history, open };
}

/** Percent change from the session's first observed price. */
export function sessionChange(price: number, open: number | undefined): number {
  return open ? ((price - open) / open) * 100 : 0;
}

/** Collapse points to whole-second times (last value wins), as the chart library requires. */
export function toChartPoints(points: PricePoint[]): PricePoint[] {
  const out: PricePoint[] = [];
  for (const p of points) {
    const time = Math.floor(p.time);
    if (out.length && out[out.length - 1].time === time) out[out.length - 1] = { time, value: p.value };
    else out.push({ time, value: p.value });
  }
  return out;
}
