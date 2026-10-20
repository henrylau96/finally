import { useState } from "react";
import { formatPct } from "@/lib/format";
import type { Quote } from "@/lib/usePriceStream";
import PriceCell from "./PriceCell";
import Sparkline from "./Sparkline";

export default function WatchlistRow({
  ticker,
  quote,
  history,
  live,
  selected,
  onSelect,
  onRemove,
  onError,
}: {
  ticker: string;
  quote?: Quote;
  history: number[];
  live: boolean;
  selected: boolean;
  onSelect: (ticker: string) => void;
  onRemove: (ticker: string) => Promise<string | null>;
  onError: (msg: string) => void;
}) {
  const [pending, setPending] = useState(false);
  const pct = quote?.day_change_pct;
  const color = !live || !pct ? "text-text-muted" : pct > 0 ? "text-up" : "text-down";

  async function remove(e: React.MouseEvent) {
    e.stopPropagation();
    setPending(true);
    const err = await onRemove(ticker);
    setPending(false);
    if (err) onError(err);
  }

  return (
    <div
      role="row"
      aria-selected={selected}
      data-testid={"watchlist-row-" + ticker}
      tabIndex={0}
      onClick={() => onSelect(ticker)}
      onKeyDown={(e) => {
        if (e.key !== "Enter" && e.key !== " ") return;
        e.preventDefault();
        onSelect(ticker);
      }}
      className={
        "group grid h-8 cursor-pointer grid-cols-[72px_1fr_72px_72px_24px] items-center gap-2 border-b border-l-2 border-b-border px-2 transition-colors duration-100 hover:bg-row-hover " +
        (selected ? "border-l-primary bg-row-hover" : "border-l-transparent")
      }
    >
      <span role="gridcell" className="font-mono font-semibold">{ticker}</span>
      <span role="gridcell" className="text-right">
        <PriceCell ticker={ticker} price={quote?.price} direction={quote?.direction} live={live} />
      </span>
      <span
        role="gridcell"
        data-testid={"day-change-" + ticker}
        className={"text-right font-mono tabular-nums " + color}
      >
        {formatPct(pct)}
      </span>
      <span role="gridcell">
        <Sparkline ticker={ticker} points={history} up={(pct ?? 0) >= 0} />
      </span>
      <span role="gridcell">
        <button
          type="button"
          data-testid={"watchlist-remove-" + ticker}
          aria-label={"Remove " + ticker + " from watchlist"}
          title={"Remove " + ticker}
          disabled={pending}
          onClick={remove}
          onKeyDown={(e) => e.stopPropagation()}
          className="remove-btn max-lg:opacity-100 h-6 w-6 text-base text-text-muted opacity-0 transition-opacity duration-100 hover:text-down focus-visible:text-down focus-visible:opacity-100 group-focus-within:opacity-100 group-hover:opacity-100"
        >
          ×
        </button>
      </span>
    </div>
  );
}
