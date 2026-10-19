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
}: {
  ticker: string;
  quote?: Quote;
  history: number[];
  live: boolean;
  selected: boolean;
  onSelect: (ticker: string) => void;
}) {
  const pct = quote?.day_change_pct;
  const color = !live || !pct ? "text-text-muted" : pct > 0 ? "text-up" : "text-down";
  return (
    <div
      role="row"
      data-testid={"watchlist-row-" + ticker}
      tabIndex={0}
      onClick={() => onSelect(ticker)}
      onKeyDown={(e) => e.key === "Enter" && onSelect(ticker)}
      className={
        "flex h-8 cursor-pointer items-center gap-2 border-b border-l-2 border-b-border px-2 transition-colors duration-100 hover:bg-row-hover " +
        (selected ? "border-l-primary bg-row-hover" : "border-l-transparent")
      }
    >
      <span className="w-[72px] font-mono font-semibold">{ticker}</span>
      <span className="min-w-[88px] flex-1 text-right">
        <PriceCell ticker={ticker} price={quote?.price} direction={quote?.direction} live={live} />
      </span>
      <span
        data-testid={"day-change-" + ticker}
        className={"w-[72px] text-right font-mono tabular-nums " + color}
      >
        {formatPct(pct)}
      </span>
      <span className="w-16">
        <Sparkline points={history} up={(pct ?? 0) >= 0} />
      </span>
    </div>
  );
}
