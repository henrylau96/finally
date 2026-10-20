"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import { useChat } from "@/lib/useChat";
import ChatMessage from "./ChatMessage";

const EXAMPLES = ["How is my portfolio doing?", "Buy 5 NVDA", "Add PYPL"];

function Loading() {
  return (
    <div
      data-testid="chat-loading"
      role="status"
      aria-label="FinAlly is thinking"
      className="flex w-fit gap-1 self-start border border-border bg-bg p-2"
    >
      {[0, 150, 300].map((delay) => (
        <span
          key={delay}
          className="status-pulse h-1 w-1 rounded-full bg-text-muted"
          style={{ animationDelay: `${delay}ms` }}
        />
      ))}
    </div>
  );
}

export default function ChatDock({ onActions }: { onActions: () => void }) {
  const [collapsed, setCollapsed] = useState(false);
  const [draft, setDraft] = useState("");
  const { messages, pending, send } = useChat(onActions);
  const listRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const wasPending = useRef(false);
  const label = collapsed ? "Expand chat panel" : "Collapse chat panel";

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setCollapsed(!window.matchMedia("(min-width: 1280px)").matches);
  }, []);

  useEffect(() => {
    const el = listRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [messages, pending, collapsed]);

  useEffect(() => {
    if (wasPending.current && !pending) inputRef.current?.focus();
    wasPending.current = pending;
  }, [pending]);

  function submit(e: FormEvent) {
    e.preventDefault();
    const text = draft;
    setDraft("");
    void send(text);
  }

  return (
    <aside
      data-testid="chat-panel"
      data-collapsed={collapsed ? "true" : "false"}
      className={"flex min-h-0 flex-col border border-border bg-surface " + (collapsed ? "w-12" : "w-[360px] max-xl:absolute max-xl:inset-y-0 max-xl:right-0 max-xl:z-10")}
    >
      <div className={"flex items-center px-2 py-1 " + (collapsed ? "justify-center" : "justify-between border-b border-border")}>
        {!collapsed && (
          <h2 className="text-xs font-semibold uppercase tracking-[0.05em] text-text-muted">FinAlly AI</h2>
        )}
        <button
          type="button"
          data-testid="chat-toggle"
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
      <div
        ref={listRef}
        data-testid="chat-messages"
        role="log"
        aria-live="polite"
        className={"min-h-0 flex-1 flex-col gap-2 overflow-y-auto p-2 " + (collapsed ? "hidden" : "flex")}
      >
        {messages.length === 0 && !pending && (
          <div
            data-testid="chat-empty"
            className="flex h-full flex-col items-center justify-center gap-4 p-4 text-center"
          >
            <div>
              <p className="text-sm text-text-muted">Ask FinAlly about your portfolio.</p>
              <p className="text-xs text-text-muted">
                It can analyze positions, place trades and manage your watchlist.
              </p>
            </div>
            <div className="flex w-full flex-col gap-1">
              {EXAMPLES.map((text) => (
                <button
                  key={text}
                  type="button"
                  data-testid="chat-example"
                  onClick={() => {
                    setDraft(text);
                    inputRef.current?.focus();
                  }}
                  className="h-8 w-full border border-border px-2 text-left text-xs text-text hover:bg-row-hover"
                >
                  {text}
                </button>
              ))}
            </div>
          </div>
        )}
        {messages.map((m) => (
          <ChatMessage key={m.id} entry={m} />
        ))}
        {pending && <Loading />}
      </div>
      <form
        data-testid="chat-form"
        aria-busy={pending}
        onSubmit={submit}
        className={"gap-1 border-t border-border p-2 " + (collapsed ? "hidden" : "flex")}
      >
        <input
          ref={inputRef}
          data-testid="chat-input"
          type="text"
          value={draft}
          disabled={pending}
          maxLength={2000}
          autoComplete="off"
          placeholder="Ask FinAlly..."
          aria-label="Message FinAlly"
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => e.key === "Escape" && setDraft("")}
          className="h-8 min-w-0 flex-1 border border-border bg-bg px-2 text-sm text-text placeholder:text-text-muted disabled:cursor-progress"
        />
        <button
          data-testid="chat-send"
          type="submit"
          aria-label="Send message"
          disabled={pending || !draft.trim()}
          className="h-8 w-16 bg-submit text-sm font-semibold text-text hover:brightness-110 disabled:cursor-progress disabled:opacity-50"
        >
          Send
        </button>
      </form>
    </aside>
  );
}
