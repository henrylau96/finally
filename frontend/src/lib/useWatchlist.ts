"use client";

import { useCallback, useEffect, useState } from "react";

export type WatchlistItem = {
  ticker: string;
  price: number | null;
  previous_price: number | null;
  direction: "up" | "down" | "flat" | null;
  day_change_pct: number | null;
  added_at: string;
};

export function useWatchlist() {
  const [rows, setRows] = useState<WatchlistItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  const load = useCallback(async () => {
    try {
      const res = await fetch("/api/watchlist");
      if (res.ok) {
        setRows(await res.json());
        setError(false);
      } else {
        setError(true);
      }
    } catch {
      setError(true);
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load();
  }, [load]);

  return { rows, loading, error, load };
}
