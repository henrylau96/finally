import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useChat, type ChatEntry } from "@/lib/useChat";
import ChatDock from "./ChatDock";

vi.mock("@/lib/useChat", () => ({ useChat: vi.fn() }));

const send = vi.fn();
const state = (messages: ChatEntry[], pending = false) =>
  vi.mocked(useChat).mockReturnValue({ messages, pending, send });

const entry = (role: "user" | "assistant", actions: ChatEntry["actions"] = null): ChatEntry => ({
  id: crypto.randomUUID(),
  role,
  content: role + " says hi",
  actions,
  created_at: "2026-01-01T00:00:00Z",
});

const originalMatchMedia = window.matchMedia;
const wide = (matches: boolean) =>
  (window.matchMedia = ((media: string) => ({ ...originalMatchMedia(media), matches })) as typeof window.matchMedia);

describe("ChatDock", () => {
  beforeEach(() => state([]));
  afterEach(() => {
    window.matchMedia = originalMatchMedia;
  });

  it("shows the loading indicator and disables input while pending", () => {
    state([entry("user")], true);
    render(<ChatDock onActions={vi.fn()} />);
    expect(screen.getByTestId("chat-loading")).toBeInTheDocument();
    expect(screen.getByTestId("chat-input")).toBeDisabled();
  });

  it("renders messages with success and failure action chips", () => {
    state([
      entry("user"),
      entry("assistant", [
        { type: "trade", ticker: "AAPL", side: "buy", quantity: 5, price: 190, ok: true },
        { type: "trade", ticker: "TSLA", side: "buy", quantity: 999, ok: false, error: "Insufficient cash" },
      ]),
    ]);
    render(<ChatDock onActions={vi.fn()} />);
    expect(screen.getAllByTestId("chat-message")).toHaveLength(2);
    const chips = screen.getAllByTestId("chat-action");
    expect(chips[0]).toHaveAttribute("data-ok", "true");
    expect(chips[1]).toHaveAttribute("data-ok", "false");
  });

  it("shows the empty state with no messages", () => {
    render(<ChatDock onActions={vi.fn()} />);
    expect(screen.getByTestId("chat-empty")).toBeInTheDocument();
  });

  it("starts collapsed on narrow screens but keeps messages in the DOM", () => {
    render(<ChatDock onActions={vi.fn()} />);
    expect(screen.getByTestId("chat-panel")).toHaveAttribute("data-collapsed", "true");
    expect(screen.getByTestId("chat-messages")).toBeInTheDocument();
  });

  it("starts expanded on wide screens and toggles", async () => {
    wide(true);
    render(<ChatDock onActions={vi.fn()} />);
    expect(screen.getByTestId("chat-panel")).toHaveAttribute("data-collapsed", "false");
    await userEvent.setup().click(screen.getByTestId("chat-toggle"));
    expect(screen.getByTestId("chat-panel")).toHaveAttribute("data-collapsed", "true");
  });
});
