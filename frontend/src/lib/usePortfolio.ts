"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { Portfolio } from "./portfolio";

export function usePortfolio() {
  const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
  const [version, setVersion] = useState(0);
  const seq = useRef(0);

  const refresh = useCallback(async () => {
    const id = ++seq.current;
    let data: Portfolio | null = null;
    try {
      const res = await fetch("/api/portfolio");
      if (res.ok) data = await res.json();
    } catch {}
    if (id !== seq.current || !data) return;
    setPortfolio(data);
    setVersion((v) => v + 1);
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  /** Place a market order; resolves to an error message, or null on success. */
  const trade = useCallback(
    async (ticker: string, quantity: number, side: "buy" | "sell"): Promise<string | null> => {
      const generic = "Could not place the trade. Try again.";
      try {
        const res = await fetch("/api/portfolio/trade", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ ticker, quantity, side }),
        });
        if (res.ok) {
          await refresh();
          setVersion((v) => v + 1);
          return null;
        }
        const body = await res.json();
        if (res.status === 400 && typeof body.detail === "string") return body.detail;
        if (res.status === 422) {
          const onTicker = Array.isArray(body.detail) && body.detail.some((d: { loc?: unknown[] }) => d.loc?.includes("ticker"));
          return onTicker ? "Enter a ticker of 1-5 letters." : "Enter a quantity above 0 (up to 4 decimals).";
        }
      } catch {}
      await refresh();
      return generic;
    },
    [refresh],
  );

  return { portfolio, version, refresh, trade };
}
