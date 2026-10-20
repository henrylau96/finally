import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { derivePositions, type Portfolio } from "@/lib/portfolio";
import PositionsTable from "./PositionsTable";

const pos = (ticker: string, quantity: number, avg_cost: number, price: number) => ({
  ticker,
  quantity,
  avg_cost,
  current_price: price,
  market_value: price * quantity,
  unrealized_pnl: 0,
  pnl_pct: 0,
});

const portfolio: Portfolio = {
  cash_balance: 100,
  total_value: 0,
  unrealized_pnl: 0,
  positions: [pos("AAPL", 10, 100, 120), pos("TSLA", 5, 200, 150)],
};

function setup(rows = derivePositions(portfolio, {}).rows) {
  const onSelect = vi.fn();
  render(<PositionsTable rows={rows} quotes={{}} live selected="AAPL" onSelect={onSelect} />);
  return onSelect;
}

describe("PositionsTable", () => {
  it("renders rows with quantity and gain/loss state", () => {
    setup();
    expect(screen.getByTestId("position-qty-AAPL")).toHaveTextContent("10");
    expect(screen.getByTestId("position-pnl-AAPL")).toHaveAttribute("data-pnl", "up");
    expect(screen.getByTestId("position-pnl-TSLA")).toHaveAttribute("data-pnl", "down");
  });

  it("shows the empty state", () => {
    setup([]);
    expect(screen.getByTestId("positions-empty")).toBeInTheDocument();
  });

  it("selects a ticker on row click", async () => {
    const onSelect = setup();
    await userEvent.setup().click(screen.getByTestId("position-row-TSLA"));
    expect(onSelect).toHaveBeenCalledWith("TSLA");
  });
});
