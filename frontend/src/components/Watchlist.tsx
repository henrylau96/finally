"use client";

import { useState, type FormEvent } from "react";
import { sessionChange, type PriceState } from "@/lib/prices";
import { WatchlistRow } from "./WatchlistRow";

interface Props {
  tickers: string[];
  stream: PriceState;
  selected: string;
  error: string;
  onSelect: (ticker: string) => void;
  onAdd: (ticker: string) => void;
  onRemove: (ticker: string) => void;
}

/** Watched tickers with live prices, plus an input to add more. */
export function Watchlist({ tickers, stream, selected, error, onSelect, onAdd, onRemove }: Props) {
  const [input, setInput] = useState("");

  const submit = (e: FormEvent) => {
    e.preventDefault();
    const ticker = input.trim().toUpperCase();
    if (!ticker) return;
    onAdd(ticker);
    setInput("");
  };

  return (
    <section data-testid="watchlist" className="flex min-h-0 flex-col bg-panel">
      <h2 className="px-3 pt-2.5 pb-1.5 text-xs font-medium text-muted">Watchlist</h2>
      <div className="min-h-0 flex-1 overflow-y-auto">
        {tickers.map((t) => {
          const last = stream.prices[t]?.price;
          return (
            <WatchlistRow
              key={t}
              ticker={t}
              last={last}
              change={last != null ? sessionChange(last, stream.open[t]) : 0}
              points={stream.history[t] ?? []}
              selected={t === selected}
              onSelect={onSelect}
              onRemove={onRemove}
            />
          );
        })}
      </div>
      <form onSubmit={submit} className="flex gap-1.5 border-t border-rule p-2">
        <input
          data-testid="watchlist-add-input"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Add ticker"
          aria-label="Ticker to add"
          className="min-w-0 flex-1 rounded-sm border border-rule bg-ink px-2 py-1 uppercase placeholder:normal-case placeholder:text-muted"
        />
        <button
          data-testid="watchlist-add-button"
          type="submit"
          className="rounded-sm border border-primary px-2.5 py-1 text-primary hover:bg-primary hover:text-ink"
        >
          Add
        </button>
      </form>
      {error && <p className="px-2 pb-2 text-xs text-down">{error}</p>}
    </section>
  );
}
