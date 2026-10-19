import type { Status } from "@/lib/usePriceStream";
import ConnectionStatus from "./ConnectionStatus";

export default function Header({ status, hasConnected }: { status: Status; hasConnected: boolean }) {
  return (
    <header className="flex h-12 shrink-0 items-center gap-6 border border-border bg-surface px-4">
      <span className="text-base font-semibold text-accent">FinAlly</span>
      <div className="flex items-baseline gap-2">
        <span className="text-xs font-semibold uppercase tracking-[0.05em] text-text-muted">Total value</span>
        <span data-testid="total-value" className="font-mono text-xl font-semibold">--</span>
      </div>
      <div className="flex items-baseline gap-2">
        <span className="text-xs font-semibold uppercase tracking-[0.05em] text-text-muted">Cash</span>
        <span data-testid="cash-balance" className="font-mono">--</span>
      </div>
      <div className="ml-auto">
        <ConnectionStatus status={status} hasConnected={hasConnected} />
      </div>
    </header>
  );
}
