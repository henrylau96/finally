"use client";

import { useEffect, useState } from "react";
import type { ChartPoint } from "@/lib/usePriceStream";

export const RETRY_MS = 60_000;

/** Daily history per ticker from /api/history, loaded one ticker at a time; failures retry after RETRY_MS. */
export function useHistorySeeds(tickers: string[]): Record<string, ChartPoint[]> {
  const [seeds, setSeeds] = useState<Record<string, ChartPoint[]>>({});
  const [failed, setFailed] = useState<string[]>([]);
  const key = tickers.join(",");

  useEffect(() => {
    const next = key.split(",").find((t) => t !== "" && !(t in seeds) && !failed.includes(t));
    if (!next) {
      if (failed.length === 0) return;
      const timer = setTimeout(() => setFailed([]), RETRY_MS);
      return () => clearTimeout(timer);
    }
    let cancelled = false;
    fetch("/api/history/" + next)
      .then((res) => (res.ok ? res.json() : Promise.reject(res.status)))
      .then((points: ChartPoint[]) => {
        if (!cancelled) setSeeds((prev) => ({ ...prev, [next]: points }));
      })
      .catch(() => {
        if (!cancelled) setFailed((prev) => [...prev, next]);
      });
    return () => {
      cancelled = true;
    };
  }, [key, seeds, failed]);

  return seeds;
}
