"use client";

import { useState } from "react";
import type { Side } from "@/lib/types";

interface Props {
  ticker: string;
  onTickerChange: (ticker: string) => void;
  onTrade: (ticker: string, quantity: number, side: Side) => Promise<void>;
}

/** Market order entry: ticker, quantity, buy and sell. */
export function TradeBar({ ticker, onTickerChange, onTrade }: Props) {
  const [quantity, setQuantity] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (side: Side) => {
    const qty = Number(quantity);
    if (!ticker || !(qty > 0)) {
      setError("Enter a ticker and a quantity above zero");
      return;
    }
    setBusy(true);
    setError("");
    try {
      await onTrade(ticker, qty, side);
      setQuantity("");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const input = "rounded-sm border border-rule bg-ink px-2 py-1.5";
  return (
    <div className="flex flex-wrap items-center gap-2 border-t border-rule px-3 py-2">
      <input
        data-testid="trade-ticker"
        aria-label="Trade ticker"
        value={ticker}
        onChange={(e) => onTickerChange(e.target.value.toUpperCase())}
        className={`${input} w-24 uppercase`}
      />
      <input
        data-testid="trade-quantity"
        aria-label="Quantity"
        type="number"
        min="0"
        step="any"
        placeholder="Qty"
        value={quantity}
        onChange={(e) => setQuantity(e.target.value)}
        className={`${input} num w-24 placeholder:text-muted`}
      />
      <button
        data-testid="buy-button"
        disabled={busy}
        onClick={() => submit("buy")}
        className="rounded-sm bg-secondary px-4 py-1.5 font-medium text-white hover:brightness-125 disabled:opacity-50"
      >
        Buy
      </button>
      <button
        data-testid="sell-button"
        disabled={busy}
        onClick={() => submit("sell")}
        className="rounded-sm border border-secondary px-4 py-1.5 font-medium hover:bg-secondary disabled:opacity-50"
      >
        Sell
      </button>
      {error && (
        <span data-testid="trade-error" role="alert" className="text-xs text-down">
          {error}
        </span>
      )}
    </div>
  );
}
