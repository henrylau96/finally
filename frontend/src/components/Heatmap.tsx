"use client";

import { formatPct, formatPrice } from "@/lib/format";
import { pnlState, type PositionRow } from "@/lib/portfolio";
import { squarify } from "@/lib/treemap";
import { useSize } from "@/lib/useSize";
import Panel from "./Panel";

function fill(pct: number): string {
  const state = pnlState(pct);
  if (state === "flat") return "var(--color-row-hover)";
  const a = 0.25 + 0.55 * Math.min(Math.abs(pct) / 10, 1);
  return state === "positive" ? `rgba(63,185,80,${a})` : `rgba(248,81,73,${a})`;
}

export default function Heatmap({
  rows,
  selected,
  onSelect,
}: {
  rows: PositionRow[] | null;
  selected: string;
  onSelect: (t: string) => void;
}) {
  const [ref, { width, height }] = useSize<HTMLDivElement>();
  const rects = rows ? squarify(rows.map((r) => ({ id: r.ticker, value: r.market_value })), width, height) : [];
  const byTicker = new Map((rows ?? []).map((r) => [r.ticker, r]));
  return (
    <Panel title="Heatmap" testId="heatmap" bodyClassName="overflow-hidden">
      <div ref={ref} className="relative h-full w-full">
        {rows && rows.length === 0 && (
          <div data-testid="heatmap-empty" className="flex h-full flex-col items-center justify-center gap-1 text-center">
            <p className="text-sm text-text-muted">No positions yet.</p>
            <p className="text-xs text-text-muted">Your holdings appear here after your first trade.</p>
          </div>
        )}
        {rects.map((r) => {
          const row = byTicker.get(r.id)!;
          const pct = row.pnl_pct;
          const select = () => onSelect(row.ticker);
          return (
            <div
              key={r.id}
              data-testid={"heatmap-cell-" + row.ticker}
              data-pnl={pnlState(pct)}
              data-selected={row.ticker === selected}
              role="img"
              aria-label={`${row.ticker}: ${formatPct(pct)}, market value ${formatPrice(row.market_value)}`}
              title={`${row.ticker} ${formatPct(pct)}`}
              tabIndex={0}
              onClick={select}
              onKeyDown={(e) => {
                if (e.key !== "Enter" && e.key !== " ") return;
                e.preventDefault();
                select();
              }}
              style={{ left: r.x, top: r.y, width: r.w, height: r.h, backgroundColor: fill(pct) }}
              className="absolute box-border cursor-pointer overflow-hidden border border-bg p-2 transition-[background-color] duration-300 hover:outline hover:outline-1 hover:-outline-offset-1 hover:outline-text-muted motion-reduce:transition-none"
            >
              {r.w >= 56 && r.h >= 28 && (
                <>
                  <div className="truncate font-mono text-sm font-semibold">{row.ticker}</div>
                  {r.h >= 44 && <div className="font-mono text-xs tabular-nums">{formatPct(pct)}</div>}
                </>
              )}
            </div>
          );
        })}
      </div>
    </Panel>
  );
}
