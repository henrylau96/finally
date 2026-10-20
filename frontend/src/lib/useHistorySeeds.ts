"use client";

import { useEffect, useState } from "react";
import type { ChartPoint } from "@/lib/usePriceStream";

/** Daily history per ticker from /api/history, loaded one ticker at a time and once per page load. */
export function useHistorySeeds(tickers: string[]): Record<string, ChartPoint[]> {
  const [seeds, setSeeds] = useState<Record<string, ChartPoint[]>>({});
  const key = tickers.join(",");

  useEffect(() => {
    const next = key.split(",").find((t) => t !== "" && !(t in seeds));
    if (!next) return;
    let cancelled = false;
    const store = (points: ChartPoint[]) => {
      if (!cancelled) setSeeds((prev) => ({ ...prev, [next]: points }));
    };
    fetch("/api/history/" + next)
      .then((res) => (res.ok ? res.json() : []))
      .then(store)
      .catch(() => store([]));
    return () => {
      cancelled = true;
    };
  }, [key, seeds]);

  return seeds;
}
