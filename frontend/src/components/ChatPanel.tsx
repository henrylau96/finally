"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import type { ChatMessage as Message } from "@/lib/types";
import { ChatMessage } from "./ChatMessage";

type Entry = Pick<Message, "role" | "content" | "actions">;

interface Props {
  messages: Entry[];
  loading: boolean;
  onSend: (text: string) => void;
}

/** Collapsible assistant sidebar: history, loading indicator, message input. */
export function ChatPanel({ messages, loading, onSend }: Props) {
  const [open, setOpen] = useState(true);
  const [text, setText] = useState("");
  const list = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (list.current) list.current.scrollTop = list.current.scrollHeight;
  }, [messages, loading]);

  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (!text.trim() || loading) return;
    onSend(text.trim());
    setText("");
  };

  return (
    <aside
      data-testid="chat-panel"
      data-open={open}
      className={`flex min-h-0 flex-col border-l border-rule bg-panel ${open ? "w-[340px]" : "w-10"}`}
    >
      <div className="flex items-center justify-between px-3 py-2">
        {open && <h2 className="text-xs font-medium text-muted">Assistant</h2>}
        <button
          onClick={() => setOpen(!open)}
          aria-label={open ? "Collapse assistant" : "Expand assistant"}
          className="text-muted hover:text-text"
        >
          {open ? "»" : "«"}
        </button>
      </div>
      {open && (
        <>
          <div ref={list} className="flex min-h-0 flex-1 flex-col gap-2 overflow-y-auto px-3 pb-2">
            {messages.length === 0 && (
              <p className="text-muted">
                Ask about your portfolio, or tell me to trade. Try &quot;buy 5 AAPL&quot; or &quot;how
                concentrated am I?&quot;
              </p>
            )}
            {messages.map((m, i) => (
              <ChatMessage key={i} message={m} />
            ))}
            {loading && (
              <div data-testid="chat-loading" className="flex gap-1 self-start px-1 py-2" aria-label="Assistant is thinking">
                <span className="loading-dot h-1.5 w-1.5 rounded-full bg-accent" />
                <span className="loading-dot h-1.5 w-1.5 rounded-full bg-accent [animation-delay:150ms]" />
                <span className="loading-dot h-1.5 w-1.5 rounded-full bg-accent [animation-delay:300ms]" />
              </div>
            )}
          </div>
          <form onSubmit={submit} className="flex gap-1.5 border-t border-rule p-2">
            <input
              data-testid="chat-input"
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="Message the assistant"
              aria-label="Message"
              className="min-w-0 flex-1 rounded-sm border border-rule bg-ink px-2 py-1.5 placeholder:text-muted"
            />
            <button
              data-testid="chat-send"
              type="submit"
              disabled={loading}
              className="rounded-sm bg-secondary px-3 py-1.5 font-medium text-white hover:brightness-125 disabled:opacity-50"
            >
              Send
            </button>
          </form>
        </>
      )}
    </aside>
  );
}
