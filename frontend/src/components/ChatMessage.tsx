import { formatPrice, formatQty } from "@/lib/format";
import type { ChatAction, ChatEntry } from "@/lib/useChat";

function chipText(a: ChatAction): string {
  const ticker = a.ticker.toUpperCase();
  if (!a.ok) {
    const what = a.type === "trade" ? `${a.side} ${formatQty(a.quantity)} ${ticker}` : `${a.action} ${ticker}`;
    return `Failed: ${what}. ${a.error || "Could not complete the action."}`;
  }
  if (a.type === "watchlist") return `${a.action === "add" ? "Added" : "Removed"} ${ticker}`;
  const verb = a.side === "buy" ? "Bought" : "Sold";
  return `${verb} ${formatQty(a.quantity)} ${ticker} @ ${formatPrice(a.price)}`;
}

function Chip({ action }: { action: ChatAction }) {
  const tone = action.ok ? "up" : "down";
  return (
    <span
      data-testid="chat-action"
      data-ok={action.ok ? "true" : "false"}
      data-type={action.type}
      className={`break-words border px-2 py-1 font-mono text-xs tabular-nums ${action.ok ? "text-up" : "text-down"}`}
      style={{
        borderColor: `color-mix(in srgb, var(--color-${tone}) 40%, transparent)`,
        backgroundColor: `color-mix(in srgb, var(--color-${tone}) 12%, transparent)`,
      }}
    >
      {chipText(action)}
    </span>
  );
}

export default function ChatMessage({ entry }: { entry: ChatEntry }) {
  const user = entry.role === "user";
  const time = new Date(entry.created_at).toLocaleTimeString("en-GB");
  return (
    <div
      data-testid="chat-message"
      data-role={entry.role}
      data-error={entry.error ? "true" : undefined}
      title={time}
      className={
        "min-w-0 max-w-[85%] border border-border p-2 text-sm " +
        (user ? "self-end bg-row-hover" : "self-start bg-bg") +
        (entry.error ? " border-l-2 border-l-down" : "")
      }
    >
      <span className="sr-only">{user ? "You said" : "FinAlly said"}: </span>
      <span className="whitespace-pre-wrap break-words">{entry.content}</span>
      {entry.actions && entry.actions.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1">
          {entry.actions.map((a, i) => (
            <Chip key={i} action={a} />
          ))}
        </div>
      )}
    </div>
  );
}
