import type { ChatMessage, ChatResponse, Portfolio, Side, Snapshot, WatchlistItem } from "./types";

/** Fetch JSON from the same-origin API, throwing the server's `detail` on failure. */
async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? `Request failed (${res.status})`);
  }
  return res.status === 204 ? (undefined as T) : res.json();
}

export const api = {
  portfolio: () => request<Portfolio>("/api/portfolio"),
  history: () => request<Snapshot[]>("/api/portfolio/history"),
  trade: (ticker: string, quantity: number, side: Side) =>
    request<{ portfolio: Portfolio }>("/api/portfolio/trade", {
      method: "POST",
      body: JSON.stringify({ ticker, quantity, side }),
    }),
  watchlist: () => request<WatchlistItem[]>("/api/watchlist"),
  addTicker: (ticker: string) =>
    request<{ ticker: string }>("/api/watchlist", {
      method: "POST",
      body: JSON.stringify({ ticker }),
    }),
  removeTicker: (ticker: string) =>
    request<void>(`/api/watchlist/${encodeURIComponent(ticker)}`, { method: "DELETE" }),
  chat: (message: string) =>
    request<ChatResponse>("/api/chat", { method: "POST", body: JSON.stringify({ message }) }),
  chatHistory: () => request<ChatMessage[]>("/api/chat/history"),
};
