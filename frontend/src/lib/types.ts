export type Direction = "up" | "down" | "flat";

export interface PriceUpdate {
  ticker: string;
  price: number;
  previous_price: number;
  timestamp: number;
  change: number;
  change_percent: number;
  direction: Direction;
}

export interface PricePoint {
  time: number;
  value: number;
}

export interface Position {
  ticker: string;
  quantity: number;
  avg_cost: number;
  current_price: number;
  market_value: number;
  unrealized_pnl: number;
  unrealized_pnl_percent: number;
}

export interface Portfolio {
  cash_balance: number;
  total_value: number;
  total_unrealized_pnl: number;
  positions: Position[];
}

export interface Snapshot {
  total_value: number;
  recorded_at: string;
}

export interface WatchlistItem {
  ticker: string;
  price: number | null;
  previous_price: number | null;
  change: number | null;
  change_percent: number | null;
  direction: Direction | null;
}

export type Side = "buy" | "sell";
export type ActionStatus = "executed" | "failed";

export interface TradeAction {
  ticker: string;
  side: Side;
  quantity: number;
  status: ActionStatus;
  price?: number | null;
  error?: string | null;
}

export interface WatchlistAction {
  ticker: string;
  action: "add" | "remove";
  status: ActionStatus;
  error?: string | null;
}

export interface ChatResponse {
  message: string;
  trades: TradeAction[];
  watchlist_changes: WatchlistAction[];
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  actions: { trades?: TradeAction[]; watchlist_changes?: WatchlistAction[] } | null;
  created_at: string;
}

export type ConnectionStatus = "connected" | "reconnecting" | "disconnected";
