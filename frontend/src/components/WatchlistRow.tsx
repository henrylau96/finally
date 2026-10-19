"use client";

import { useFlash } from "@/hooks/useFlash";
import { percent, price } from "@/lib/format";
import type { PricePoint } from "@/lib/types";
import { Sparkline } from "./Sparkline";

interface Props {
  ticker: string;
  last?: number;
  change: number;
  points: PricePoint[];
  selected: boolean;
  onSelect: (ticker: string) => void;
  onRemove: (ticker: string) => void;
}

/** One watchlist line: ticker, sparkline, flashing price, session change, remove. */
export function WatchlistRow({ ticker, last, change, points, selected, onSelect, onRemove }: Props) {
  const flash = useFlash(last);
  const tone = change > 0 ? "text-up" : change < 0 ? "text-down" : "text-muted";
  return (
    <div
      data-testid={`watchlist-row-${ticker}`}
      role="button"
      tabIndex={0}
      aria-pressed={selected}
      onClick={() => onSelect(ticker)}
      onKeyDown={(e) => e.key === "Enter" && onSelect(ticker)}
      className={`group grid cursor-pointer grid-cols-[3.5rem_1fr_4.5rem_3.75rem_1rem] items-center gap-1.5 border-l-2 px-3 py-1.5 hover:bg-raised ${
        selected ? "border-accent bg-raised" : "border-transparent"
      }`}
    >
      <span className={`font-semibold ${selected ? "text-accent" : ""}`}>{ticker}</span>
      <Sparkline points={points} color={change < 0 ? "var(--color-down)" : "var(--color-up)"} />
      <span data-testid={`price-${ticker}`} className={`num flash-fade rounded-sm px-1 text-right ${flash}`}>
        {last != null ? price(last) : "--"}
      </span>
      <span className={`num text-right text-xs ${tone}`}>{last != null ? percent(change) : ""}</span>
      <button
        data-testid={`watchlist-remove-${ticker}`}
        aria-label={`Remove ${ticker}`}
        onClick={(e) => {
          e.stopPropagation();
          onRemove(ticker);
        }}
        className="text-muted opacity-0 hover:text-down focus:opacity-100 group-hover:opacity-100"
      >
        ×
      </button>
    </div>
  );
}
