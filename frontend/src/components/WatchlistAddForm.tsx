"use client";

import { useRef, useState } from "react";

const INVALID = "Enter 1-5 letters, e.g. PYPL.";

export default function WatchlistAddForm({
  onAdd,
  onError,
}: {
  onAdd: (ticker: string) => Promise<string | null>;
  onError: (msg: string) => void;
}) {
  const [value, setValue] = useState("");
  const [pending, setPending] = useState(false);
  const input = useRef<HTMLInputElement>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    const ticker = value.trim().toUpperCase();
    if (!/^[A-Z]{1,5}$/.test(ticker)) return onError(INVALID);
    onError("");
    setPending(true);
    const err = await onAdd(ticker);
    setPending(false);
    setTimeout(() => input.current?.focus());
    if (err) return onError(err);
    setValue("");
  }

  return (
    <form onSubmit={submit} className="flex gap-1 bg-surface p-2">
      <input
        ref={input}
        data-testid="watchlist-add-input"
        type="text"
        placeholder="Add ticker, e.g. PYPL"
        aria-label="Ticker symbol"
        maxLength={5}
        autoComplete="off"
        spellCheck={false}
        value={value}
        disabled={pending}
        onChange={(e) => {
          setValue(e.target.value.toUpperCase());
          onError("");
        }}
        onKeyDown={(e) => {
          if (e.key === "Escape") {
            setValue("");
            onError("");
          }
        }}
        className="h-8 flex-1 border border-border bg-bg px-2 font-mono text-sm uppercase"
      />
      <button
        data-testid="watchlist-add-button"
        type="submit"
        aria-label="Add ticker"
        aria-busy={pending}
        disabled={pending}
        className="h-8 w-14 bg-submit text-sm font-semibold text-text hover:brightness-110 disabled:cursor-progress disabled:opacity-50"
      >
        Add
      </button>
    </form>
  );
}
