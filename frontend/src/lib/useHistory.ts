"use client";

import { useEffect, useState } from "react";
import type { ChartPoint } from "@/lib/usePriceStream";

const EMPTY: ChartPoint[] = [];

/** Daily history for one ticker from /api/history; empty until loaded or when unavailable. */
export function useHistory(ticker: string): ChartPoint[] {
  const [state, setState] = useState({ ticker: "", points: EMPTY });

  useEffect(() => {
    if (ticker === "") return;
    let cancelled = false;
    fetch("/api/history/" + ticker)
      .then((res) => (res.ok ? res.json() : null))
      .then((points: ChartPoint[] | null) => {
        if (!cancelled && points) setState({ ticker, points });
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [ticker]);

  return state.ticker === ticker ? state.points : EMPTY;
}
