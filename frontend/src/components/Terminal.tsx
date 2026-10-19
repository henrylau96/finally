"use client";

import { useCallback, useEffect, useState } from "react";
import { usePriceStream } from "@/hooks/usePriceStream";
import { api } from "@/lib/api";
import { revaluePortfolio } from "@/lib/portfolio";
import type { ChatMessage as Message, Portfolio, Side, Snapshot } from "@/lib/types";
import { ChatPanel } from "./ChatPanel";
import { Header } from "./Header";
import { Heatmap } from "./Heatmap";
import { PnlChart } from "./PnlChart";
import { PositionsTable } from "./PositionsTable";
import { PriceChart } from "./PriceChart";
import { TradeBar } from "./TradeBar";
import { Watchlist } from "./Watchlist";

type Entry = Pick<Message, "role" | "content" | "actions">;

const emptyPortfolio: Portfolio = { cash_balance: 0, total_value: 0, total_unrealized_pnl: 0, positions: [] };
const REFRESH_MS = 30_000;

/** The whole trading workstation: owns server state and wires panels together. */
export function Terminal() {
  const stream = usePriceStream();
  const [portfolio, setPortfolio] = useState(emptyPortfolio);
  const [snapshots, setSnapshots] = useState<Snapshot[]>([]);
  const [watchlist, setWatchlist] = useState<string[]>([]);
  const [watchError, setWatchError] = useState("");
  const [selected, setSelected] = useState("");
  const [tradeTicker, setTradeTicker] = useState("");
  const [messages, setMessages] = useState<Entry[]>([]);
  const [chatLoading, setChatLoading] = useState(false);

  const refreshPortfolio = useCallback(async () => {
    const [p, h] = await Promise.all([api.portfolio(), api.history()]);
    setPortfolio(p);
    setSnapshots(h);
  }, []);

  const refreshWatchlist = useCallback(async () => {
    const tickers = (await api.watchlist()).map((w) => w.ticker);
    setWatchlist(tickers);
    setSelected((s) => s || tickers[0] || "");
    setTradeTicker((t) => t || tickers[0] || "");
    return tickers;
  }, []);

  /** Move selection and trade ticker off tickers that left the watchlist. */
  const dropRemoved = (removed: string[], remaining: string[]) => {
    const next = (t: string) => (removed.includes(t) ? remaining[0] ?? "" : t);
    setSelected(next);
    setTradeTicker(next);
  };

  useEffect(() => {
    refreshPortfolio();
    refreshWatchlist();
    api.chatHistory().then(setMessages);
    const id = setInterval(refreshPortfolio, REFRESH_MS);
    return () => clearInterval(id);
  }, [refreshPortfolio, refreshWatchlist]);

  const select = (ticker: string) => {
    setSelected(ticker);
    setTradeTicker(ticker);
  };

  const trade = async (ticker: string, quantity: number, side: Side) => {
    await api.trade(ticker, quantity, side);
    await refreshPortfolio();
  };

  const addTicker = async (ticker: string) => {
    setWatchError("");
    try {
      await api.addTicker(ticker);
      await refreshWatchlist();
    } catch (e) {
      setWatchError((e as Error).message);
    }
  };

  const removeTicker = async (ticker: string) => {
    setWatchError("");
    try {
      await api.removeTicker(ticker);
      dropRemoved([ticker], await refreshWatchlist());
    } catch (e) {
      setWatchError((e as Error).message);
    }
  };

  const sendChat = async (text: string) => {
    setMessages((m) => [...m, { role: "user", content: text, actions: null }]);
    setChatLoading(true);
    try {
      const res = await api.chat(text);
      const actions = { trades: res.trades, watchlist_changes: res.watchlist_changes };
      setMessages((m) => [...m, { role: "assistant", content: res.message, actions }]);
      const [, remaining] = await Promise.all([refreshPortfolio(), refreshWatchlist()]);
      const removed = res.watchlist_changes
        .filter((w) => w.action === "remove" && w.status === "executed")
        .map((w) => w.ticker);
      dropRemoved(removed, remaining);
    } catch (e) {
      setMessages((m) => [...m, { role: "assistant", content: `Request failed: ${(e as Error).message}`, actions: null }]);
    } finally {
      setChatLoading(false);
    }
  };

  const live = revaluePortfolio(portfolio, stream.prices);

  return (
    <div className="flex h-screen flex-col">
      <Header
        totalValue={live.total_value}
        cash={live.cash_balance}
        pnl={live.total_unrealized_pnl}
        status={stream.status}
      />
      <div className="flex min-h-0 flex-1">
        <div className="grid min-h-0 flex-1 grid-cols-[340px_1fr] gap-px bg-rule">
          <Watchlist
            tickers={watchlist}
            stream={stream}
            selected={selected}
            error={watchError}
            onSelect={select}
            onAdd={addTicker}
            onRemove={removeTicker}
          />
          <div className="grid min-h-0 grid-rows-[minmax(260px,1fr)_minmax(200px,0.8fr)_minmax(150px,0.6fr)] gap-px">
            <div className="flex min-h-0 flex-col bg-panel">
              <PriceChart ticker={selected} points={stream.history[selected] ?? []} />
              <TradeBar ticker={tradeTicker} onTickerChange={setTradeTicker} onTrade={trade} />
            </div>
            <div className="grid min-h-0 grid-cols-2 gap-px">
              <Heatmap positions={live.positions} onSelect={select} />
              <PnlChart snapshots={snapshots} />
            </div>
            <PositionsTable positions={live.positions} onSelect={select} />
          </div>
        </div>
        <ChatPanel messages={messages} loading={chatLoading} onSend={sendChat} />
      </div>
    </div>
  );
}
