import { money, signedMoney } from "@/lib/format";
import type { ConnectionStatus } from "@/lib/types";

const dotColor: Record<ConnectionStatus, string> = {
  connected: "bg-up",
  reconnecting: "bg-accent",
  disconnected: "bg-down",
};

interface Props {
  totalValue: number;
  cash: number;
  pnl: number;
  status: ConnectionStatus;
}

/** Top bar: brand, live portfolio value, cash, unrealized P&L, stream status. */
export function Header({ totalValue, cash, pnl, status }: Props) {
  return (
    <header className="flex items-end gap-8 border-b border-rule bg-panel px-4 py-2">
      <div className="pb-0.5 text-lg font-semibold tracking-tight">
        Fin<span className="text-accent">Ally</span>
      </div>
      <div>
        <div className="text-xs text-muted">Portfolio value</div>
        <div data-testid="total-value" className="num text-2xl leading-none text-accent">
          {money(totalValue)}
        </div>
      </div>
      <div>
        <div className="text-xs text-muted">Cash</div>
        <div data-testid="cash-balance" className="num text-base leading-tight">{money(cash)}</div>
      </div>
      <div>
        <div className="text-xs text-muted">Unrealized P&amp;L</div>
        <div className={`num text-base leading-tight ${pnl > 0 ? "text-up" : pnl < 0 ? "text-down" : ""}`}>
          {signedMoney(pnl)}
        </div>
      </div>
      <div
        data-testid="connection-status"
        data-status={status}
        className="ml-auto flex items-center gap-1.5 pb-1 text-xs text-muted"
        title={`Price stream ${status}`}
      >
        <span className={`h-2 w-2 rounded-full ${dotColor[status]}`} />
        {status === "connected" ? "Live" : status === "reconnecting" ? "Reconnecting" : "Offline"}
      </div>
    </header>
  );
}
