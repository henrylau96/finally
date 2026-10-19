import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ChatPanel } from "./ChatPanel";

const messages = [
  { role: "user" as const, content: "buy 10 AAPL", actions: null },
  {
    role: "assistant" as const,
    content: "Done.",
    actions: {
      trades: [{ ticker: "AAPL", side: "buy" as const, quantity: 10, status: "executed" as const, price: 190.1, error: null }],
      watchlist_changes: [{ ticker: "PYPL", action: "add" as const, status: "failed" as const, error: "Already watched" }],
    },
  },
];

describe("ChatPanel", () => {
  it("renders messages with roles and inline actions", () => {
    render(<ChatPanel messages={messages} loading={false} onSend={vi.fn()} />);
    const rendered = screen.getAllByTestId("chat-message");
    expect(rendered.map((m) => m.dataset.role)).toEqual(["user", "assistant"]);
    const actions = screen.getAllByTestId("chat-action");
    expect(actions[0]).toHaveTextContent("Bought 10 AAPL at $190.10");
    expect(actions[1]).toHaveTextContent("Could not add PYPL: Already watched");
  });

  it("shows the loading indicator only while waiting", () => {
    const { rerender } = render(<ChatPanel messages={[]} loading={true} onSend={vi.fn()} />);
    expect(screen.getByTestId("chat-loading")).toBeInTheDocument();
    rerender(<ChatPanel messages={[]} loading={false} onSend={vi.fn()} />);
    expect(screen.queryByTestId("chat-loading")).toBeNull();
  });

  it("sends the typed message and clears the input", async () => {
    const onSend = vi.fn();
    render(<ChatPanel messages={[]} loading={false} onSend={onSend} />);
    await userEvent.type(screen.getByTestId("chat-input"), "hello");
    await userEvent.click(screen.getByTestId("chat-send"));
    expect(onSend).toHaveBeenCalledWith("hello");
    expect(screen.getByTestId("chat-input")).toHaveValue("");
  });
});
