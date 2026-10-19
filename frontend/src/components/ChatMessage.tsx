import { money, shares } from "@/lib/format";
import type { ChatMessage as Message, TradeAction, WatchlistAction } from "@/lib/types";

function tradeText(t: TradeAction): string {
  const verb = t.side === "buy" ? "Bought" : "Sold";
  if (t.status === "executed") {
    return `${verb} ${shares(t.quantity)} ${t.ticker}${t.price != null ? ` at ${money(t.price)}` : ""}`;
  }
  return `Could not ${t.side} ${shares(t.quantity)} ${t.ticker}: ${t.error ?? "failed"}`;
}

function watchText(w: WatchlistAction): string {
  if (w.status === "executed") return `${w.action === "add" ? "Added" : "Removed"} ${w.ticker} ${w.action === "add" ? "to" : "from"} watchlist`;
  return `Could not ${w.action} ${w.ticker}: ${w.error ?? "failed"}`;
}

/** A single chat bubble with inline trade and watchlist confirmations. */
export function ChatMessage({ message }: { message: Pick<Message, "role" | "content" | "actions"> }) {
  const isUser = message.role === "user";
  const actions = [
    ...(message.actions?.trades ?? []).map((t) => ({ ok: t.status === "executed", text: tradeText(t) })),
    ...(message.actions?.watchlist_changes ?? []).map((w) => ({ ok: w.status === "executed", text: watchText(w) })),
  ];
  return (
    <div
      data-testid="chat-message"
      data-role={message.role}
      className={`max-w-[92%] rounded-sm px-2.5 py-1.5 ${isUser ? "self-end bg-primary/15" : "self-start bg-raised"}`}
    >
      <p className="whitespace-pre-wrap leading-snug">{message.content}</p>
      {actions.map((a, i) => (
        <p
          key={i}
          data-testid="chat-action"
          data-ok={a.ok}
          className={`mt-1 border-l-2 pl-2 text-xs ${a.ok ? "border-up text-up" : "border-down text-down"}`}
        >
          {a.text}
        </p>
      ))}
    </div>
  );
}
