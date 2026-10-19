import { percent } from "@/lib/format";
import { pnlSign } from "@/lib/portfolio";
import { squarify } from "@/lib/treemap";
import type { Position } from "@/lib/types";

/** Background color scaled by P&L percent: deeper green/red for larger moves. */
function cellColor(pct: number): string {
  const strength = Math.min(Math.abs(pct) / 5, 1);
  const alpha = 0.25 + strength * 0.6;
  if (pct > 0.005) return `rgb(38 178 111 / ${alpha})`;
  if (pct < -0.005) return `rgb(229 72 77 / ${alpha})`;
  return "var(--color-raised)";
}

/** Treemap of positions sized by market value and colored by unrealized P&L. */
export function Heatmap({ positions, onSelect }: { positions: Position[]; onSelect: (t: string) => void }) {
  const rects = squarify(positions.map((p) => ({ key: p.ticker, value: p.market_value })));
  const byTicker = Object.fromEntries(positions.map((p) => [p.ticker, p]));
  return (
    <section className="flex min-h-0 flex-col bg-panel">
      <h2 className="px-3 pt-2.5 pb-1.5 text-xs font-medium text-muted">Holdings heatmap</h2>
      <div data-testid="heatmap" className="relative mx-3 mb-3 min-h-0 flex-1">
        {rects.map((r) => {
          const p = byTicker[r.key];
          return (
            <button
              key={r.key}
              data-testid={`heatmap-cell-${r.key}`}
              data-pnl={pnlSign(p.unrealized_pnl)}
              onClick={() => onSelect(r.key)}
              title={`${r.key} ${percent(p.unrealized_pnl_percent)}`}
              className="absolute flex flex-col items-center justify-center overflow-hidden border border-ink text-xs"
              style={{
                left: `${r.x * 100}%`,
                top: `${r.y * 100}%`,
                width: `${r.w * 100}%`,
                height: `${r.h * 100}%`,
                background: cellColor(p.unrealized_pnl_percent),
              }}
            >
              <span className="font-semibold">{r.key}</span>
              <span className="num">{percent(p.unrealized_pnl_percent)}</span>
            </button>
          );
        })}
        {rects.length === 0 && <p className="text-muted">Positions appear here once you hold shares.</p>}
      </div>
    </section>
  );
}
