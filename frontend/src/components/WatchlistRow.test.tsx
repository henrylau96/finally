import { act, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { WatchlistRow } from "./WatchlistRow";

const props = { ticker: "AAPL", change: 0, points: [], selected: false, onSelect: vi.fn(), onRemove: vi.fn() };

describe("WatchlistRow", () => {
  it("renders ticker and price", () => {
    render(<WatchlistRow {...props} last={190.5} />);
    expect(screen.getByTestId("watchlist-row-AAPL")).toHaveTextContent("AAPL");
    expect(screen.getByTestId("price-AAPL")).toHaveTextContent("190.50");
  });

  it("flashes up on an uptick and down on a downtick, then clears", () => {
    vi.useFakeTimers();
    const { rerender } = render(<WatchlistRow {...props} last={100} />);
    const cell = screen.getByTestId("price-AAPL");
    expect(cell).not.toHaveClass("flash-up");

    rerender(<WatchlistRow {...props} last={101} />);
    expect(cell).toHaveClass("flash-up");
    act(() => vi.advanceTimersByTime(100));
    expect(cell).not.toHaveClass("flash-up");

    rerender(<WatchlistRow {...props} last={99} />);
    expect(cell).toHaveClass("flash-down");
    vi.useRealTimers();
  });

  it("remove does not select the row", () => {
    const onSelect = vi.fn();
    const onRemove = vi.fn();
    render(<WatchlistRow {...props} last={1} onSelect={onSelect} onRemove={onRemove} />);
    screen.getByTestId("watchlist-remove-AAPL").click();
    expect(onRemove).toHaveBeenCalledWith("AAPL");
    expect(onSelect).not.toHaveBeenCalled();
  });
});
