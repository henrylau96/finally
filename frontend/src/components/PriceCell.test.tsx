import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import PriceCell from "./PriceCell";

describe("PriceCell", () => {
  it("flashes up and down synchronously on a live price change", () => {
    const { rerender } = render(<PriceCell ticker="AAPL" price={100} live />);
    rerender(<PriceCell ticker="AAPL" price={101} direction="up" live />);
    expect(screen.getByTestId("price-AAPL")).toHaveAttribute("data-flash", "up");
    rerender(<PriceCell ticker="AAPL" price={100} direction="down" live />);
    expect(screen.getByTestId("price-AAPL")).toHaveAttribute("data-flash", "down");
  });

  it("does not flash when not live", () => {
    render(<PriceCell ticker="AAPL" price={101} direction="up" live={false} />);
    expect(screen.getByTestId("price-AAPL")).not.toHaveAttribute("data-flash");
  });

  it("shows the formatted price", () => {
    render(<PriceCell ticker="AAPL" price={1234.5} live />);
    expect(screen.getByTestId("price-AAPL")).toHaveTextContent("1,234.50");
  });
});
