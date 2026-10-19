import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { Position } from "@/lib/types";
import { Heatmap } from "./Heatmap";
import { PositionsTable } from "./PositionsTable";
import { TradeBar } from "./TradeBar";

const pos = (ticker: string, pnl: number): Position => ({
  ticker, quantity: 10, avg_cost: 100, current_price: 100 + pnl / 10,
  market_value: 1000 + pnl, unrealized_pnl: pnl, unrealized_pnl_percent: pnl / 10,
});

const positions = [pos("AAPL", 50), pos("TSLA", -20), pos("MSFT", 0)];

describe("Heatmap", () => {
  it("renders one cell per position with P&L sign", () => {
    render(<Heatmap positions={positions} onSelect={vi.fn()} />);
    expect(screen.getByTestId("heatmap-cell-AAPL").dataset.pnl).toBe("positive");
    expect(screen.getByTestId("heatmap-cell-TSLA").dataset.pnl).toBe("negative");
    expect(screen.getByTestId("heatmap-cell-MSFT").dataset.pnl).toBe("flat");
  });
});

describe("PositionsTable", () => {
  it("renders a row per position with P&L", () => {
    render(<PositionsTable positions={positions} onSelect={vi.fn()} />);
    expect(screen.getByTestId("position-row-AAPL")).toHaveTextContent("+$50.00");
    expect(screen.getByTestId("position-row-TSLA")).toHaveTextContent("-$20.00");
  });
});

describe("TradeBar", () => {
  it("shows the server error when a trade fails", async () => {
    const onTrade = vi.fn().mockRejectedValue(new Error("Insufficient cash"));
    render(<TradeBar ticker="AAPL" onTickerChange={vi.fn()} onTrade={onTrade} />);
    await userEvent.type(screen.getByTestId("trade-quantity"), "5");
    await userEvent.click(screen.getByTestId("buy-button"));
    expect(onTrade).toHaveBeenCalledWith("AAPL", 5, "buy");
    expect(await screen.findByTestId("trade-error")).toHaveTextContent("Insufficient cash");
  });
});
