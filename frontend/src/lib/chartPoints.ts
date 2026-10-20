import type { ChartPoint } from "@/lib/usePriceStream";

const SEED_CLOSES = 30;
const SPARK_POINTS = 120;

/** Sparkline values: `ticks` unchanged without a seed, else the last daily closes merged with live chart points. */
export function sparklineValues(seed: ChartPoint[], chart: ChartPoint[], ticks: number[]): number[] {
  if (seed.length === 0) return ticks;
  const merged = mergePoints(seed.slice(-SEED_CLOSES), chart);
  return merged.map((p) => p.value).slice(-SPARK_POINTS);
}

/** History first, then live points after it; a live point at the last history time replaces it, so time stays strictly ascending for lightweight-charts. */
export function mergePoints(history: ChartPoint[], live: ChartPoint[]): ChartPoint[] {
  if (history.length === 0) return live;
  const end = history[history.length - 1].time;
  const kept = live.filter((p) => p.time >= end);
  const base = kept[0]?.time === end ? history.slice(0, -1) : history;
  return [...base, ...kept];
}
