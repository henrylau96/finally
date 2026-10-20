import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { Quote } from "@/lib/usePriceStream";
import Watchlist from "./Watchlist";

const quotes: Record<string, Quote> = {
  AAPL: { ticker: "AAPL", price: 190.5, previous_price: 190, timestamp: 1, direction: "up", day_change_pct: 0.5 },
  MSFT: { ticker: "MSFT", price: 400, previous_price: 400, timestamp: 1, direction: "flat", day_change_pct: 0 },
};

function setup(over: Partial<Parameters<typeof Watchlist>[0]> = {}) {
  const props = {
    tickers: ["AAPL", "MSFT"],
    quotes,
    history: { AAPL: [1, 2, 3], MSFT: [4, 5] },
    status: "connected" as const,
    selected: "AAPL",
    onSelect: vi.fn(),
    onAdd: vi.fn().mockResolvedValue(null),
    onRemove: vi.fn().mockResolvedValue(null),
    loading: false,
    loadError: false,
    ...over,
  };
  render(<Watchlist {...props} />);
  return props;
}

describe("Watchlist", () => {
  it("renders a row per ticker with price and sparkline points", () => {
    setup();
    expect(screen.getByTestId("watchlist-row-AAPL")).toBeInTheDocument();
    expect(screen.getByTestId("watchlist-row-MSFT")).toBeInTheDocument();
    expect(screen.getByTestId("price-AAPL")).toHaveTextContent("$190.50");
    expect(screen.getByTestId("sparkline-AAPL")).toHaveAttribute("data-points", "3");
  });

  it("adds an uppercased ticker", async () => {
    const props = setup();
    await userEvent.setup().type(screen.getByTestId("watchlist-add-input"), "pypl");
    await userEvent.setup().click(screen.getByTestId("watchlist-add-button"));
    expect(props.onAdd).toHaveBeenCalledWith("PYPL");
  });

  it("shows the add error", async () => {
    setup({ onAdd: vi.fn().mockResolvedValue("Unknown ticker") });
    const user = userEvent.setup();
    await user.type(screen.getByTestId("watchlist-add-input"), "zzzz");
    await user.click(screen.getByTestId("watchlist-add-button"));
    expect(await screen.findByTestId("watchlist-add-error")).toHaveTextContent("Unknown ticker");
  });

  it("removes without selecting", async () => {
    const props = setup();
    await userEvent.setup().click(screen.getByTestId("watchlist-remove-AAPL"));
    expect(props.onRemove).toHaveBeenCalledWith("AAPL");
    expect(props.onSelect).not.toHaveBeenCalled();
  });

  it("shows the empty state", () => {
    setup({ tickers: [] });
    expect(screen.getByTestId("watchlist-empty")).toBeInTheDocument();
  });
});
