import { money, percent, price, shares, signedMoney } from "@/lib/format";
import type { Position } from "@/lib/types";

const tone = (v: number) => (v > 0 ? "text-up" : v < 0 ? "text-down" : "");

/** Holdings with cost basis and unrealized P&L. */
export function PositionsTable({ positions, onSelect }: { positions: Position[]; onSelect: (t: string) => void }) {
  return (
    <section className="flex min-h-0 flex-col bg-panel">
      <h2 className="px-3 pt-2.5 pb-1.5 text-xs font-medium text-muted">Positions</h2>
      <div className="min-h-0 flex-1 overflow-auto">
        <table data-testid="positions-table" className="w-full text-right">
          <thead className="sticky top-0 bg-panel text-xs text-muted">
            <tr>
              <th className="px-3 py-1 text-left font-normal">Ticker</th>
              <th className="px-3 py-1 font-normal">Qty</th>
              <th className="px-3 py-1 font-normal">Avg cost</th>
              <th className="px-3 py-1 font-normal">Price</th>
              <th className="px-3 py-1 font-normal">Market value</th>
              <th className="px-3 py-1 font-normal">Unrealized P&amp;L</th>
              <th className="px-3 py-1 font-normal">Change</th>
            </tr>
          </thead>
          <tbody className="num">
            {positions.map((p) => (
              <tr
                key={p.ticker}
                data-testid={`position-row-${p.ticker}`}
                onClick={() => onSelect(p.ticker)}
                className="cursor-pointer border-t border-rule/60 hover:bg-raised"
              >
                <td className="px-3 py-1 text-left font-sans font-semibold">{p.ticker}</td>
                <td className="px-3 py-1">{shares(p.quantity)}</td>
                <td className="px-3 py-1">{price(p.avg_cost)}</td>
                <td className="px-3 py-1">{price(p.current_price)}</td>
                <td className="px-3 py-1">{money(p.market_value)}</td>
                <td className={`px-3 py-1 ${tone(p.unrealized_pnl)}`}>{signedMoney(p.unrealized_pnl)}</td>
                <td className={`px-3 py-1 ${tone(p.unrealized_pnl)}`}>{percent(p.unrealized_pnl_percent)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {positions.length === 0 && (
          <p className="px-3 py-4 text-muted">No positions yet. Buy shares with the trade bar or ask the assistant.</p>
        )}
      </div>
    </section>
  );
}
