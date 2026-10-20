import { useState } from "react";
import type { Quote, Status } from "@/lib/usePriceStream";
import Panel from "./Panel";
import WatchlistAddForm from "./WatchlistAddForm";
import WatchlistRow from "./WatchlistRow";

const GRID = "grid grid-cols-[72px_1fr_72px_72px_24px] gap-2";
const HEADERS = ["Symbol", "Price", "Day %", "Chart"];

function notice(
  status: Status,
  loading: boolean,
  loadError: boolean,
  waiting: boolean,
): string {
  if (loadError) return "Could not load the watchlist. Reload the page.";
  if (status === "disconnected") return "Price stream closed. Reload the page to retry.";
  if (status === "reconnecting") return "Reconnecting to price stream. Prices may be stale.";
  if (loading) return "Loading watchlist...";
  if (status === "connected" && waiting) return "Waiting for prices...";
  return "";
}

export default function Watchlist({
  tickers,
  quotes,
  history,
  status,
  selected,
  onSelect,
  onAdd,
  onRemove,
  loading,
  loadError,
}: {
  tickers: string[];
  quotes: Record<string, Quote>;
  history: Record<string, number[]>;
  status: Status;
  selected: string;
  onSelect: (ticker: string) => void;
  onAdd: (ticker: string) => Promise<string | null>;
  onRemove: (ticker: string) => Promise<string | null>;
  loading: boolean;
  loadError: boolean;
}) {
  const [error, setError] = useState("");
  const waiting = tickers.length > 0 && !tickers.some((t) => quotes[t]);
  const text = notice(status, loading, loadError, waiting);
  return (
    <Panel title="Watchlist" active testId="watchlist">
      <WatchlistAddForm onAdd={onAdd} onError={setError} />
      <div className="h-6 px-2 text-xs">
        {error && (
          <p role="alert" data-testid="watchlist-add-error" className="text-down">
            {error}
          </p>
        )}
      </div>
      <div
        role="status"
        aria-live="polite"
        title={text}
        className={
          "h-6 overflow-hidden truncate px-2 text-xs " + (loadError ? "text-down" : "text-text-muted")
        }
      >
        {text}
      </div>
      <div role="grid" aria-label="Watchlist">
        <div role="rowgroup">
          <div
            role="row"
            className={
              GRID +
              " h-6 items-center border-b border-border border-l-2 border-l-transparent px-2 text-xs font-semibold uppercase tracking-[0.05em] text-text-muted"
            }
          >
            <span role="columnheader">{HEADERS[0]}</span>
            <span role="columnheader" className="text-right">{HEADERS[1]}</span>
            <span role="columnheader" className="text-right">{HEADERS[2]}</span>
            <span role="columnheader" className="text-center">{HEADERS[3]}</span>
            <span role="columnheader" aria-label="Actions" />
          </div>
        </div>
        <div role="rowgroup">
          {tickers.map((t) => (
            <WatchlistRow
              key={t}
              ticker={t}
              quote={quotes[t]}
              history={history[t] ?? []}
              live={status === "connected"}
              selected={selected === t}
              onSelect={onSelect}
              onRemove={onRemove}
              onError={setError}
            />
          ))}
        </div>
      </div>
      {!loading && !loadError && tickers.length === 0 && (
        <p data-testid="watchlist-empty" className="p-4 text-center text-sm text-text-muted">
          No tickers yet. Add one above.
        </p>
      )}
    </Panel>
  );
}
