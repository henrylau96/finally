"use client";

import { useEffect, useState } from "react";
import { applyBatch, emptyPriceState, type PriceState } from "@/lib/prices";
import type { ConnectionStatus } from "@/lib/types";

/** Subscribe to the SSE price stream; returns accumulated prices and connection status. */
export function usePriceStream(url = "/api/stream/prices") {
  const [state, setState] = useState<PriceState>(emptyPriceState);
  const [status, setStatus] = useState<ConnectionStatus>("reconnecting");

  useEffect(() => {
    const source = new EventSource(url);
    source.onopen = () => setStatus("connected");
    source.onmessage = (event) => {
      setStatus("connected");
      setState((s) => applyBatch(s, JSON.parse(event.data)));
    };
    source.onerror = () =>
      setStatus(source.readyState === EventSource.CLOSED ? "disconnected" : "reconnecting");
    return () => source.close();
  }, [url]);

  return { ...state, status };
}
