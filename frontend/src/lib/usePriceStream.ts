"use client";

import { useEffect, useState } from "react";

export type Quote = {
  ticker: string;
  price: number;
  previous_price: number;
  timestamp: number;
  direction: "up" | "down" | "flat";
  day_change_pct: number;
};
export type Status = "connected" | "reconnecting" | "disconnected";

const MAX_POINTS = 120;

export function usePriceStream() {
  const [status, setStatus] = useState<Status>("reconnecting");
  const [quotes, setQuotes] = useState<Record<string, Quote>>({});
  const [history, setHistory] = useState<Record<string, number[]>>({});

  useEffect(() => {
    const es = new EventSource("/api/stream/prices");
    es.onopen = () => setStatus("connected");
    es.onerror = () =>
      setStatus(es.readyState === EventSource.CLOSED ? "disconnected" : "reconnecting");
    es.onmessage = (e) => {
      const next: Record<string, Quote> = JSON.parse(e.data);
      setQuotes(next);
      setHistory((prev) =>
        Object.fromEntries(
          Object.entries(next).map(([t, q]) => [t, [...(prev[t] ?? []), q.price].slice(-MAX_POINTS)]),
        ),
      );
    };
    return () => es.close();
  }, []);

  return { status, quotes, history };
}
