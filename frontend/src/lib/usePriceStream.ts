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

export type ChartPoint = { time: number; value: number };

const MAX_POINTS = 120;
const CHART_POINTS = 1000;
const STALE_SECONDS = 300;

/** Append a tick as strictly ascending whole-second points, replacing a same-second value. */
function appendPoint(arr: ChartPoint[], timestamp: number, value: number): ChartPoint[] {
  const time = Math.floor(timestamp);
  const last = arr[arr.length - 1];
  if (last && time < last.time) return arr;
  const base = last && time === last.time ? arr.slice(0, -1) : arr;
  return [...base, { time, value }].slice(-CHART_POINTS);
}

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

  const [chart, setChart] = useState<Record<string, ChartPoint[]>>({});
  const [asOf, setAsOf] = useState<number | null>(null);

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
      const newest = Math.max(0, ...Object.values(next).map((q) => q.timestamp));
      setAsOf(newest && Date.now() / 1000 - newest > STALE_SECONDS ? newest : null);
      setQuotes((prev) => withRenderedDirection(prev, next));
      setHistory((prev) =>
        Object.fromEntries(
          Object.entries(next).map(([t, q]) => [t, [...(prev[t] ?? []), q.price].slice(-MAX_POINTS)]),
        ),
      );
      setChart((prev) =>
        Object.fromEntries(
          Object.entries(next).map(([t, q]) => [t, appendPoint(prev[t] ?? [], q.timestamp, q.price)]),
        ),
      );
    };
    return () => es.close();
  }, []);

  return { status, hasConnected, quotes, history, chart, asOf };
}
