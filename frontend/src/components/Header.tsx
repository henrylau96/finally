import type { Status } from "@/lib/usePriceStream";
import { formatPrice } from "@/lib/format";
import ConnectionStatus from "./ConnectionStatus";

type Props = { status: Status; hasConnected: boolean; total?: number; cash?: number };

export default function Header({ status, hasConnected, total, cash }: Props) {
  return (
    <header className="flex h-12 shrink-0 items-center gap-6 border border-border bg-surface px-4">
      <span className="text-base font-semibold text-accent">FinAlly</span>
      <div className="flex items-baseline gap-2">
        <span className="text-xs font-semibold uppercase tracking-[0.05em] text-text-muted">Total value</span>
        <span
          data-testid="total-value"
          className={"font-mono text-xl font-semibold" + (status === "connected" ? "" : " text-text-muted")}
        >
          {formatPrice(total)}
        </span>
      </div>
      <div className="flex items-baseline gap-2">
        <span className="text-xs font-semibold uppercase tracking-[0.05em] text-text-muted">Cash</span>
        <span data-testid="cash-balance" className="font-mono">{formatPrice(cash)}</span>
      </div>
      <div className="ml-auto">
        <ConnectionStatus status={status} hasConnected={hasConnected} />
      </div>
    </header>
  );
}
