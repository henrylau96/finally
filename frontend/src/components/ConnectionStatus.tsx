import type { Status } from "@/lib/usePriceStream";

const DOT: Record<Status, string> = {
  connected: "bg-up",
  reconnecting: "bg-warn status-pulse",
  disconnected: "bg-down",
};

function label(status: Status, hasConnected: boolean) {
  if (status === "connected") return "Live";
  if (status === "disconnected") return "Offline";
  return hasConnected ? "Reconnecting" : "Connecting";
}

export default function ConnectionStatus({
  status,
  hasConnected,
}: {
  status: Status;
  hasConnected: boolean;
}) {
  return (
    <div
      data-testid="connection-status"
      data-status={status}
      role="status"
      aria-live="polite"
      title={"Price stream: " + status}
      className="flex items-center gap-1"
    >
      <span className={"h-2 w-2 rounded-full " + DOT[status]} />
      <span className="text-xs font-semibold text-text-muted">{label(status, hasConnected)}</span>
    </div>
  );
}
