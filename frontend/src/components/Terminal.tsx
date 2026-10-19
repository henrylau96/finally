"use client";

import { useEffect, useState } from "react";
import { usePriceStream } from "@/lib/usePriceStream";
import { useWatchlist } from "@/lib/useWatchlist";
import ChatDock from "./ChatDock";
import Header from "./Header";
import Panel from "./Panel";
import Watchlist from "./Watchlist";

function Placeholder({ children }: { children: string }) {
  return <p className="p-4 text-center text-text-muted">{children}</p>;
}

export default function Terminal() {
  const { status, hasConnected, quotes, history } = usePriceStream();
  const { rows, loading, error, add, remove } = useWatchlist();
  const [selected, setSelected] = useState("AAPL");
  useEffect(() => {
    if (loading || rows.some((r) => r.ticker === selected)) return;
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setSelected(rows[0]?.ticker ?? "");
  }, [rows, loading, selected]);
  return (
    <div className="flex h-full flex-col gap-2 p-2">
      <Header status={status} hasConnected={hasConnected} />
      <div className="grid min-h-0 flex-1 grid-cols-[minmax(320px,28%)_1fr_auto] gap-2">
        <Watchlist tickers={rows.map((r) => r.ticker)} quotes={quotes} history={history} status={status} selected={selected} onSelect={setSelected} onAdd={add} onRemove={remove} loading={loading} loadError={error} />
        <div className="grid min-h-0 min-w-0 grid-rows-[1.4fr_1fr] gap-2">
          <Panel title="Main chart" testId="main-chart" data-ticker={selected}>
            <Placeholder>Select a ticker to see its chart. Coming soon.</Placeholder>
          </Panel>
          <div className="grid min-h-0 grid-cols-3 gap-2">
            <Panel title="Heatmap" testId="heatmap">
              <Placeholder>Portfolio heatmap. Coming soon.</Placeholder>
            </Panel>
            <Panel title="Positions">
              <Placeholder>Positions. Coming soon.</Placeholder>
            </Panel>
            <Panel title="P&L" testId="pnl-chart">
              <Placeholder>P&L chart. Coming soon.</Placeholder>
            </Panel>
          </div>
        </div>
        <ChatDock />
      </div>
    </div>
  );
}
