import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import Header from "./Header";

describe("Header", () => {
  it("shows formatted total and cash", () => {
    render(<Header status="connected" hasConnected total={10000} cash={10000} asOf={null} />);
    expect(screen.getByTestId("app-header")).toBeInTheDocument();
    expect(screen.getByTestId("total-value")).toHaveTextContent("$10,000.00");
    expect(screen.getByTestId("cash-balance")).toHaveTextContent("$10,000.00");
  });

  it("shows the stale badge only when asOf is set", () => {
    const { rerender } = render(<Header status="connected" hasConnected asOf={null} />);
    expect(screen.queryByTestId("stale-badge")).not.toBeInTheDocument();
    rerender(<Header status="connected" hasConnected asOf={1760000000} />);
    expect(screen.getByTestId("stale-badge")).toBeInTheDocument();
  });
});
