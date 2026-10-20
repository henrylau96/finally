import type { Status } from "@/lib/usePriceStream";
import { formatPrice } from "@/lib/format";
import ConnectionStatus from "./ConnectionStatus";

type Props = { status: Status; hasConnected: boolean; total?: number; cash?: number; asOf?: number | null };

/** Format a unix-seconds timestamp as a New York calendar date, e.g. "Oct 17, 2026". */
function nyDate(seconds: number): string {
  return new Date(seconds * 1000).toLocaleDateString("en-US", {
    timeZone: "America/New_York",
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export default function Header({ status, hasConnected, total, cash, asOf }: Props) {
  return (
    <header data-testid="app-header" className="flex h-12 shrink-0 items-center gap-6 border border-border bg-surface px-4">
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
      <div className="ml-auto flex items-center gap-3">
        {asOf != null && (
          <span data-testid="stale-badge" className="text-xs text-text-muted">
            EOD · as of {nyDate(asOf)}
          </span>
        )}
        <ConnectionStatus status={status} hasConnected={hasConnected} />
      </div>
    </header>
  );
}
