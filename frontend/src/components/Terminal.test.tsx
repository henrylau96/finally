import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "@/lib/api";
import { Terminal } from "./Terminal";

vi.mock("@/lib/api", () => ({
  api: {
    portfolio: vi.fn(),
    history: vi.fn(),
    watchlist: vi.fn(),
    addTicker: vi.fn(),
    removeTicker: vi.fn(),
    trade: vi.fn(),
    chat: vi.fn(),
    chatHistory: vi.fn(),
  },
}));

vi.mock("./PriceChart", () => ({
  PriceChart: ({ ticker }: { ticker: string }) => <div data-testid="main-chart" data-ticker={ticker} />,
}));
vi.mock("./PnlChart", () => ({ PnlChart: () => <div data-testid="pnl-chart" /> }));

class FakeEventSource {
  static CLOSED = 2;
  readyState = 0;
  close() {}
}

const items = (tickers: string[]) =>
  tickers.map((ticker) => ({ ticker, price: null, previous_price: null, change: null, change_percent: null, direction: null }));

let watched: string[];

beforeEach(() => {
  vi.stubGlobal("EventSource", FakeEventSource);
  watched = ["AAPL", "MSFT"];
  vi.mocked(api.portfolio).mockResolvedValue({ cash_balance: 10000, total_value: 10000, total_unrealized_pnl: 0, positions: [] });
  vi.mocked(api.history).mockResolvedValue([]);
  vi.mocked(api.chatHistory).mockResolvedValue([]);
  vi.mocked(api.watchlist).mockImplementation(async () => items(watched));
  vi.mocked(api.removeTicker).mockImplementation(async (t) => {
    watched = watched.filter((w) => w !== t);
  });
});

const renderReady = async () => {
  render(<Terminal />);
  await waitFor(() => expect(screen.getByTestId("main-chart").dataset.ticker).toBe("AAPL"));
};

describe("Terminal watchlist removal", () => {
  it("moves selection and trade ticker off a removed selected ticker", async () => {
    await renderReady();
    await userEvent.click(screen.getByTestId("watchlist-remove-AAPL"));
    await waitFor(() => expect(screen.getByTestId("main-chart").dataset.ticker).toBe("MSFT"));
    expect(screen.getByTestId("trade-ticker")).toHaveValue("MSFT");
  });

  it("keeps the selection when another ticker is removed", async () => {
    await renderReady();
    await userEvent.click(screen.getByTestId("watchlist-remove-MSFT"));
    await waitFor(() => expect(screen.queryByTestId("watchlist-row-MSFT")).toBeNull());
    expect(screen.getByTestId("main-chart").dataset.ticker).toBe("AAPL");
    expect(screen.getByTestId("trade-ticker")).toHaveValue("AAPL");
  });

  it("moves selection off a ticker the assistant removed", async () => {
    vi.mocked(api.chat).mockImplementation(async () => {
      watched = ["MSFT"];
      return {
        message: "Removed AAPL",
        trades: [],
        watchlist_changes: [{ ticker: "AAPL", action: "remove", status: "executed", error: null }],
      };
    });
    await renderReady();
    await userEvent.type(screen.getByTestId("chat-input"), "remove AAPL");
    await userEvent.click(screen.getByTestId("chat-send"));
    await waitFor(() => expect(screen.getByTestId("main-chart").dataset.ticker).toBe("MSFT"));
    expect(screen.getByTestId("trade-ticker")).toHaveValue("MSFT");
  });
});
