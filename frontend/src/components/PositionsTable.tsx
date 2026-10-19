"use client";

import { formatPct, formatPrice, formatQty, formatSignedMoney } from "@/lib/format";
import { pnlState, type PositionRow } from "@/lib/portfolio";
import type { Quote } from "@/lib/usePriceStream";
import Panel from "./Panel";
import PriceCell from "./PriceCell";

const GRID = "grid grid-cols-[64px_minmax(56px,1fr)_80px_80px_80px_72px] gap-2 px-2";
const COLORS = { positive: "text-up", negative: "text-down", flat: "text-text-muted" };

export default function PositionsTable({
  rows,
  quotes,
  live,
  selected,
  onSelect,
}: {
  rows: PositionRow[] | null;
  quotes: Record<string, Quote>;
  live: boolean;
  selected: string;
  onSelect: (ticker: string) => void;
}) {
  return (
    <Panel title="Positions" testId="positions">
      {rows && rows.length === 0 ? (
        <div data-testid="positions-empty" className="flex h-full flex-col items-center justify-center">
          <p className="text-sm text-text-muted">No positions yet.</p>
          <p className="text-xs text-text-muted">Buy shares with the trade bar to see them here.</p>
        </div>
      ) : (
        <div role="grid" aria-label="Positions">
          <div role="rowgroup">
            <div
              role="row"
              className={
                GRID +
                " sticky top-0 h-6 items-center border-b border-l-2 border-b-border border-l-transparent bg-surface text-xs font-semibold uppercase tracking-[0.05em] text-text-muted"
              }
            >
              <span role="columnheader">Symbol</span>
              <span role="columnheader" className="text-right">Qty</span>
              <span role="columnheader" className="text-right">Avg cost</span>
              <span role="columnheader" className="text-right">Price</span>
              <span role="columnheader" className="text-right">P&amp;L</span>
              <span role="columnheader" className="text-right">Chg %</span>
            </div>
          </div>
          <div role="rowgroup">
            {(rows ?? []).map((r) => {
              const color = COLORS[pnlState(r.pnl_pct)];
              return (
                <div
                  key={r.ticker}
                  role="row"
                  data-testid={"position-row-" + r.ticker}
                  aria-selected={selected === r.ticker}
                  tabIndex={0}
                  onClick={() => onSelect(r.ticker)}
                  onKeyDown={(e) => {
                    if (e.key !== "Enter" && e.key !== " ") return;
                    e.preventDefault();
                    onSelect(r.ticker);
                  }}
                  className={
                    GRID +
                    " h-8 cursor-pointer items-center border-b border-l-2 border-b-border text-sm hover:bg-row-hover " +
                    (selected === r.ticker ? "border-l-primary bg-row-hover" : "border-l-transparent")
                  }
                >
                  <span role="gridcell" className="font-mono font-semibold">{r.ticker}</span>
                  <span role="gridcell" className="text-right font-mono tabular-nums">{formatQty(r.quantity)}</span>
                  <span role="gridcell" className="text-right font-mono tabular-nums">{formatPrice(r.avg_cost)}</span>
                  <span role="gridcell" className="text-right">
                    <PriceCell ticker={"pos-" + r.ticker} price={r.current_price} direction={quotes[r.ticker]?.direction} live={live} />
                  </span>
                  <span role="gridcell" className={"text-right font-mono tabular-nums " + color}>{formatSignedMoney(r.unrealized_pnl)}</span>
                  <span role="gridcell" className={"text-right font-mono tabular-nums " + color}>{formatPct(r.pnl_pct)}</span>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </Panel>
  );
}
