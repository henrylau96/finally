"use client";

import { DEFAULT_TICKERS } from "@/lib/tickers";
import { usePriceStream, type Status } from "@/lib/usePriceStream";

const DOT: Record<Status, string> = {
  connected: "bg-up",
  reconnecting: "bg-warn",
  disconnected: "bg-down",
};
const LABEL: Record<Status, string> = {
  connected: "Live",
  reconnecting: "Connecting",
  disconnected: "Offline",
};

function formatPrice(price: number) {
  return "$" + price.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export default function Terminal() {
  const { status, quotes } = usePriceStream();
  return (
    <div className="flex h-full flex-col">
      <header className="flex h-12 items-center justify-between border-b border-border bg-surface px-4">
        <span className="text-base font-semibold text-accent">FinAlly</span>
        <div
          data-testid="connection-status"
          data-status={status}
          role="status"
          aria-live="polite"
          title={"Price stream: " + status}
          className="flex items-center gap-2"
        >
          <span className={"h-2 w-2 rounded-full " + DOT[status]} />
          <span className="text-xs text-text-muted">{LABEL[status]}</span>
        </div>
      </header>
      <div className="overflow-auto">
        {DEFAULT_TICKERS.map((t) => (
          <div
            key={t}
            data-testid={"watchlist-row-" + t}
            className="flex items-center justify-between border-b border-border px-4 py-2 hover:bg-row-hover"
          >
            <span className="font-mono font-semibold">{t}</span>
            <span data-testid={"price-" + t} className="font-mono">
              {quotes[t] ? formatPrice(quotes[t].price) : "--"}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
