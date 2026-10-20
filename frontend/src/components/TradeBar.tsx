"use client";

import { useEffect, useRef, useState } from "react";

const BAD_TICKER = "Enter a ticker of 1-5 letters.";
const BAD_QTY = "Enter a quantity above 0 (up to 4 decimals).";
/** Plain decimal with at most 4 places; rejects hex, binary and exponent forms. */
const QTY = /^(\d+(\.\d{1,4})?|\.\d{1,4})$/;

export default function TradeBar({
  selected,
  onTrade,
}: {
  selected: string;
  onTrade: (ticker: string, quantity: number, side: "buy" | "sell") => Promise<string | null>;
}) {
  const [ticker, setTicker] = useState(selected);
  const [quantity, setQuantity] = useState("");
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);
  const qtyInput = useRef<HTMLInputElement>(null);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setTicker(selected);
  }, [selected]);

  async function submit(side: "buy" | "sell") {
    const sym = ticker.trim().toUpperCase();
    if (!/^[A-Z]{1,5}$/.test(sym)) return setError(BAD_TICKER);
    const text = quantity.trim();
    if (!QTY.test(text) || Number(text) <= 0) return setError(BAD_QTY);
    setError("");
    setPending(true);
    const err = await onTrade(sym, Number(text), side);
    setPending(false);
    if (err) setError(err);
    else setQuantity("");
    setTimeout(() => qtyInput.current?.focus());
  }

  function buyOnEnter(e: React.KeyboardEvent): boolean {
    if (e.key !== "Enter") return false;
    e.preventDefault();
    void submit("buy");
    return true;
  }

  const input = "h-8 border border-border bg-bg px-2 font-mono text-sm uppercase disabled:cursor-progress disabled:opacity-50";
  return (
    <form
      data-testid="trade-bar"
      aria-busy={pending}
      onSubmit={(e) => {
        e.preventDefault();
        void submit("buy");
      }}
    >
      <div className="flex gap-1 border-y border-border bg-surface p-2">
        <input
          data-testid="trade-ticker"
          type="text"
          placeholder="Ticker"
          aria-label="Trade ticker"
          maxLength={5}
          autoComplete="off"
          spellCheck={false}
          value={ticker}
          disabled={pending}
          onChange={(e) => {
            setTicker(e.target.value.toUpperCase());
            setError("");
          }}
          onKeyDown={buyOnEnter}
          className={input + " w-20"}
        />
        <input
          ref={qtyInput}
          data-testid="trade-quantity"
          type="text"
          inputMode="decimal"
          placeholder="Quantity"
          aria-label="Trade quantity"
          autoComplete="off"
          value={quantity}
          disabled={pending}
          onChange={(e) => {
            setQuantity(e.target.value);
            setError("");
          }}
          onKeyDown={(e) => {
            if (buyOnEnter(e) || e.key !== "Escape") return;
            setQuantity("");
            setError("");
          }}
          className={input + " w-24"}
        />
        <button
          data-testid="buy-button"
          type="button"
          aria-label="Buy shares"
          disabled={pending}
          onClick={() => void submit("buy")}
          className="h-8 w-14 bg-submit text-sm font-semibold text-text hover:brightness-110 disabled:cursor-progress disabled:opacity-50"
        >
          Buy
        </button>
        <button
          data-testid="sell-button"
          type="button"
          aria-label="Sell shares"
          disabled={pending}
          onClick={() => void submit("sell")}
          className="h-8 w-14 border border-submit text-sm font-semibold text-text hover:bg-[rgba(117,57,145,0.2)] disabled:cursor-progress disabled:opacity-50"
        >
          Sell
        </button>
      </div>
      <div className="h-6 px-2 text-xs">
        {error && (
          <p data-testid="trade-error" role="alert" title={error} className="truncate text-down">
            {error}
          </p>
        )}
      </div>
    </form>
  );
}
