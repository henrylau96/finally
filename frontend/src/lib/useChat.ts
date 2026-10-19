"use client";

import { useCallback, useEffect, useRef, useState } from "react";

export type ChatAction =
  | { type: "trade"; ticker: string; side: "buy" | "sell"; quantity: number; price?: number; ok: boolean; error?: string }
  | { type: "watchlist"; ticker: string; action: "add" | "remove"; ok: boolean; error?: string };

export interface ChatEntry {
  id: string;
  role: "user" | "assistant";
  content: string;
  actions: ChatAction[] | null;
  created_at: string;
  error?: boolean;
}

function localEntry(role: ChatEntry["role"], content: string, error = false): ChatEntry {
  return { id: crypto.randomUUID(), role, content, actions: null, created_at: new Date().toISOString(), error };
}

/** Chat state: loads history on mount, sends messages, reports executed actions. */
export function useChat(onActions: () => void) {
  const [messages, setMessages] = useState<ChatEntry[]>([]);
  const [pending, setPending] = useState(false);
  const pendingRef = useRef(false);
  const onActionsRef = useRef(onActions);
  useEffect(() => {
    onActionsRef.current = onActions;
  });

  useEffect(() => {
    fetch("/api/chat/history")
      .then((res) => (res.ok ? res.json() : []))
      .then((items: ChatEntry[]) => setMessages(items))
      .catch(() => {});
  }, []);

  const send = useCallback(async (text: string) => {
    const content = text.trim();
    if (!content || pendingRef.current) return;
    pendingRef.current = true;
    setPending(true);
    setMessages((prev) => [...prev, localEntry("user", content)]);
    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: content }),
      });
      if (!res.ok) throw new Error("request failed");
      const data = (await res.json()) as { message: ChatEntry };
      setMessages((prev) => [...prev, data.message]);
      if (data.message.actions && data.message.actions.length > 0) onActionsRef.current();
    } catch {
      setMessages((prev) => [...prev, localEntry("assistant", "Could not reach FinAlly. Try again.", true)]);
    } finally {
      pendingRef.current = false;
      setPending(false);
    }
  }, []);

  return { messages, pending, send };
}
