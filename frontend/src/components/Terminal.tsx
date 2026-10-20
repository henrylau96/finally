"use client";

import { useEffect, useMemo, useState } from "react";
import { derivePositions } from "@/lib/portfolio";
import { usePortfolio } from "@/lib/usePortfolio";
import { usePriceStream } from "@/lib/usePriceStream";
import { useWatchlist } from "@/lib/useWatchlist";
import ChatDock from "./ChatDock";
import Header from "./Header";
import Heatmap from "./Heatmap";
import MainChart from "./MainChart";
import Panel from "./Panel";
import PnlChart from "./PnlChart";
import PositionsTable from "./PositionsTable";
import TradeBar from "./TradeBar";
import Watchlist from "./Watchlist";

export default function Terminal() {
  const { status, hasConnected, quotes, history, chart, asOf } = usePriceStream();
  const { rows, loading, error, load, add, remove } = useWatchlist();
  const { portfolio, version, refresh, trade } = usePortfolio();
  const { rows: positionRows, total } = useMemo(() => derivePositions(portfolio, quotes), [portfolio, quotes]);
  const [selected, setSelected] = useState("");
  useEffect(() => {
    if (loading) return;
    const tickers = rows.map((r) => r.ticker);
    if (selected) return;
    const held = portfolio?.positions.map((p) => p.ticker) ?? [];
    const next = tickers.includes("AAPL") ? "AAPL" : (tickers[0] ?? held[0] ?? "");
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setSelected(next);
  }, [rows, loading, selected, portfolio]);
  return (
    <div className="flex h-full flex-col gap-2 p-2">
      <Header status={status} hasConnected={hasConnected} total={total} cash={portfolio?.cash_balance} asOf={asOf} />
      <div className="grid min-h-0 flex-1 grid-cols-[minmax(320px,28%)_1fr_auto] gap-2">
        <Watchlist tickers={rows.map((r) => r.ticker)} quotes={quotes} history={history} status={status} selected={selected} onSelect={setSelected} onAdd={add} onRemove={remove} loading={loading} loadError={error} />
        <div className="grid min-h-0 min-w-0 grid-rows-[1.4fr_auto_1fr] gap-2">
          <Panel title="Main chart" active bodyClassName="overflow-hidden">
            <MainChart ticker={selected} points={chart[selected] ?? []} price={quotes[selected]?.price} live={status === "connected"} />
          </Panel>
          <TradeBar selected={selected} onTrade={trade} />
          <div className="grid min-h-0 grid-cols-[minmax(0,1fr)_minmax(0,1.6fr)_minmax(0,1fr)] gap-2">
            <Heatmap rows={positionRows} selected={selected} onSelect={setSelected} />
            <PositionsTable rows={positionRows} quotes={quotes} live={status === "connected"} selected={selected} onSelect={setSelected} />
            <PnlChart version={version} />
          </div>
        </div>
        <ChatDock onActions={() => { void refresh(); void load(); }} />
      </div>
    </div>
  );
}
