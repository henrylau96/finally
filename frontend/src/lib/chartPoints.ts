import type { ChartPoint } from "@/lib/usePriceStream";

/** History first, then live points after it; a live point at the last history time replaces it, so time stays strictly ascending for lightweight-charts. */
export function mergePoints(history: ChartPoint[], live: ChartPoint[]): ChartPoint[] {
  if (history.length === 0) return live;
  const end = history[history.length - 1].time;
  const kept = live.filter((p) => p.time >= end);
  const base = kept[0]?.time === end ? history.slice(0, -1) : history;
  return [...base, ...kept];
}
