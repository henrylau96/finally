import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import MainChart from "./MainChart";

const series = vi.hoisted(() => ({ setData: vi.fn(), update: vi.fn() }));

vi.mock("@/lib/chartTheme", () => ({
  CHART: { primary: "#000", primaryFill: "#000", primaryFillEnd: "#000" },
  createBaseChart: () => ({
    addSeries: () => series,
    timeScale: () => ({ fitContent: vi.fn() }),
    remove: vi.fn(),
  }),
}));

const p = (time: number, value: number) => ({ time, value });
const props = { ticker: "AAPL", live: true, price: 1 };

describe("MainChart", () => {
  beforeEach(() => {
    series.setData.mockClear();
    series.update.mockClear();
  });

  it("seeds from history and hides the overlay", () => {
    const history = [p(1, 1), p(2, 2), p(3, 3)];
    render(<MainChart {...props} points={[]} history={history} />);
    expect(series.setData).toHaveBeenLastCalledWith(history);
    expect(screen.queryByTestId("main-chart-empty")).toBeNull();
  });

  it("shows the overlay with one stream point and no history", () => {
    render(<MainChart {...props} points={[p(1, 1)]} history={[]} />);
    expect(screen.getByTestId("main-chart-empty").textContent).toContain("Collecting price data for AAPL...");
  });

  it("appends a newer stream point with update", () => {
    const history = [p(1, 1), p(2, 2)];
    const { rerender } = render(<MainChart {...props} points={[]} history={history} />);
    series.setData.mockClear();
    rerender(<MainChart {...props} points={[p(3, 3)]} history={history} />);
    expect(series.update).toHaveBeenCalledWith(p(3, 3));
    expect(series.setData).not.toHaveBeenCalled();
  });

  it("re-seeds when history arrives after selection", () => {
    const { rerender } = render(<MainChart {...props} points={[p(5, 5)]} history={[]} />);
    series.setData.mockClear();
    const history = [p(1, 1), p(2, 2)];
    rerender(<MainChart {...props} points={[p(5, 5)]} history={history} />);
    expect(series.setData).toHaveBeenCalledWith([p(1, 1), p(2, 2), p(5, 5)]);
  });
});
