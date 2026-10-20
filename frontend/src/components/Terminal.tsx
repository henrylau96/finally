"use client";

import { useEffect, useMemo, useState } from "react";
import { sparklineValues } from "@/lib/chartPoints";
import { derivePositions } from "@/lib/portfolio";
import { usePortfolio } from "@/lib/usePortfolio";
import { usePriceStream } from "@/lib/usePriceStream";
import { useHistory } from "@/lib/useHistory";
import { useHistorySeeds } from "@/lib/useHistorySeeds";
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
  const seed = useHistory(selected);
  const tickers = useMemo(() => rows.map((r) => r.ticker), [rows]);
  const seeds = useHistorySeeds(tickers);
  const sparks = useMemo(
    () => Object.fromEntries(tickers.map((t) => [t, sparklineValues(seeds[t] ?? [], chart[t] ?? [], history[t] ?? [])])),
    [tickers, seeds, chart, history],
  );
  useEffect(() => {
    if (loading) return;
    if (selected) return;
    const held = portfolio?.positions.map((p) => p.ticker) ?? [];
    const next = tickers.includes("AAPL") ? "AAPL" : (tickers[0] ?? held[0] ?? "");
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setSelected(next);
  }, [tickers, loading, selected, portfolio]);
  return (
    <div className="flex h-full flex-col gap-2 p-2 max-lg:overflow-y-auto">
      <Header status={status} hasConnected={hasConnected} total={total} cash={portfolio?.cash_balance} asOf={asOf} />
      <div className="grid min-h-0 flex-1 grid-cols-[minmax(312px,30%)_1fr_48px] gap-2 max-lg:flex-none lg:grid-cols-[minmax(312px,26%)_1fr_48px] xl:grid-cols-[minmax(320px,28%)_1fr_auto]">
        <Watchlist tickers={tickers} quotes={quotes} history={sparks} status={status} selected={selected} onSelect={setSelected} onAdd={add} onRemove={remove} loading={loading} loadError={error} />
        <div className="grid min-h-0 min-w-0 grid-rows-[1.4fr_auto_1fr] gap-2 max-lg:grid-rows-[auto_auto_auto] max-lg:[&>*:first-child]:min-h-[240px]">
          <Panel title="Main chart" active bodyClassName="overflow-hidden">
            <MainChart ticker={selected} points={chart[selected] ?? []} history={seed} price={quotes[selected]?.price} live={status === "connected"} />
          </Panel>
          <TradeBar selected={selected} onTrade={trade} />
          <div className="grid min-h-0 grid-cols-[minmax(0,1fr)_minmax(0,1.6fr)_minmax(0,1fr)] gap-2 max-lg:grid-cols-2 max-lg:*:min-h-[240px] max-lg:[&>*:nth-child(2)]:order-first max-lg:[&>*:nth-child(2)]:col-span-2">
            <Heatmap rows={positionRows} selected={selected} onSelect={setSelected} />
            <PositionsTable rows={positionRows} quotes={quotes} live={status === "connected"} selected={selected} onSelect={setSelected} />
            <PnlChart version={version} />
          </div>
        </div>
        <div className="relative flex min-h-0 max-xl:w-12">
          <ChatDock onActions={() => { void refresh(); void load(); }} />
        </div>
      </div>
    </div>
  );
}
