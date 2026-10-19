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

/** Set each quote's direction against the last price the client rendered, not the server's last tick. */
function withRenderedDirection(prev: Record<string, Quote>, next: Record<string, Quote>) {
  return Object.fromEntries(
    Object.entries(next).map(([t, q]) => {
      const last = prev[t]?.price;
      const direction: Quote["direction"] =
        last === undefined || q.price === last ? "flat" : q.price > last ? "up" : "down";
      return [t, { ...q, direction }];
    }),
  );
}

export function usePriceStream() {
  const [status, setStatus] = useState<Status>("reconnecting");
  const [hasConnected, setHasConnected] = useState(false);
  const [quotes, setQuotes] = useState<Record<string, Quote>>({});
  const [history, setHistory] = useState<Record<string, number[]>>({});

  useEffect(() => {
    const es = new EventSource("/api/stream/prices");
    es.onopen = () => {
      setStatus("connected");
      setHasConnected(true);
    };
    es.onerror = () =>
      setStatus(es.readyState === EventSource.CLOSED ? "disconnected" : "reconnecting");
    es.onmessage = (e) => {
      const next: Record<string, Quote> = JSON.parse(e.data);
      setQuotes((prev) => withRenderedDirection(prev, next));
      setHistory((prev) =>
        Object.fromEntries(
          Object.entries(next).map(([t, q]) => [t, [...(prev[t] ?? []), q.price].slice(-MAX_POINTS)]),
        ),
      );
    };
    return () => es.close();
  }, []);

  return { status, hasConnected, quotes, history };
}
