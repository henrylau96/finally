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

  const add = useCallback(
    async (ticker: string): Promise<string | null> => {
      try {
        const res = await fetch("/api/watchlist", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ ticker }),
        });
        if (res.status === 422) return "Enter 1-5 letters, e.g. PYPL.";
        if (!res.ok) return "Could not add the ticker. Try again.";
        await load();
        return null;
      } catch {
        return "Could not add the ticker. Try again.";
      }
    },
    [load],
  );

  const remove = useCallback(
    async (ticker: string): Promise<string | null> => {
      try {
        const res = await fetch("/api/watchlist/" + ticker, { method: "DELETE" });
        if (res.status !== 204 && res.status !== 404) return "Could not remove " + ticker + ". Try again.";
        await load();
        return null;
      } catch {
        return "Could not remove " + ticker + ". Try again.";
      }
    },
    [load],
  );

  return { rows, loading, error, load, add, remove };
}
