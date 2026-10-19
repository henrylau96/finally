import type { Quote, Status } from "@/lib/usePriceStream";
import Panel from "./Panel";
import WatchlistRow from "./WatchlistRow";

const HEADERS = ["Symbol", "Price", "Day %", "Chart"];
const NOTE = "px-2 py-1 text-xs text-text-muted";

function Notice({ status, hasQuotes }: { status: Status; hasQuotes: boolean }) {
  if (status === "disconnected") {
    return <p className={NOTE}>Price stream closed. Reload the page to retry.</p>;
  }
  if (!hasQuotes) {
    return (
      <div className={NOTE}>
        <p className="font-semibold">Waiting for prices</p>
        <p>Prices appear as soon as the stream connects. No action needed.</p>
      </div>
    );
  }
  if (status === "reconnecting") {
    return <p className={NOTE}>Reconnecting to price stream. Prices shown may be stale.</p>;
  }
  return null;
}

export default function Watchlist({
  tickers,
  quotes,
  history,
  status,
  selected,
  onSelect,
}: {
  tickers: string[];
  quotes: Record<string, Quote>;
  history: Record<string, number[]>;
  status: Status;
  selected: string;
  onSelect: (ticker: string) => void;
}) {
  return (
    <Panel title="Watchlist" role="table">
      <Notice status={status} hasQuotes={Object.keys(quotes).length > 0} />
      <div
        role="row"
        className="flex h-6 items-center gap-2 border-b border-border px-2 pl-[10px] text-xs font-semibold uppercase tracking-[0.05em] text-text-muted"
      >
        <span className="w-[72px]">{HEADERS[0]}</span>
        <span className="min-w-[88px] flex-1 text-right">{HEADERS[1]}</span>
        <span className="w-[72px] text-right">{HEADERS[2]}</span>
        <span className="w-16 text-center">{HEADERS[3]}</span>
      </div>
      {tickers.map((t) => (
        <WatchlistRow
          key={t}
          ticker={t}
          quote={quotes[t]}
          history={history[t] ?? []}
          live={status === "connected"}
          selected={selected === t}
          onSelect={onSelect}
        />
      ))}
    </Panel>
  );
}
