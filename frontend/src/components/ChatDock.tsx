"use client";

import { useState } from "react";

export default function ChatDock() {
  const [collapsed, setCollapsed] = useState(false);
  const label = collapsed ? "Expand chat panel" : "Collapse chat panel";
  return (
    <aside
      data-testid="chat-panel"
      className={
        "flex min-h-0 flex-col border border-border bg-surface " + (collapsed ? "w-12" : "w-[360px]")
      }
    >
      <div className="flex items-center justify-between px-2 py-1">
        {!collapsed && (
          <h2 className="text-xs font-semibold uppercase tracking-[0.05em] text-text-muted">Assistant</h2>
        )}
        <button
          type="button"
          aria-expanded={!collapsed}
          aria-label={label}
          onClick={() => setCollapsed(!collapsed)}
          className="p-1 text-text-muted hover:text-text"
        >
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
            <path d={collapsed ? "M10 3 5 8l5 5" : "M6 3l5 5-5 5"} />
          </svg>
        </button>
      </div>
      {!collapsed && (
        <p className="p-4 text-center text-text-muted">AI assistant. Coming soon.</p>
      )}
    </aside>
  );
}
