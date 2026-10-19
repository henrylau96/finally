import { APIRequestContext, Locator, Page, expect } from "@playwright/test";

/** Parse a displayed money/number string like "$10,000.00" into a number. */
export function parseMoney(text: string | null): number {
  return Number((text ?? "").replace(/[^0-9.-]/g, ""));
}

/** Read the numeric value shown in a locator. */
export async function readNumber(locator: Locator): Promise<number> {
  return parseMoney(await locator.textContent());
}

/** Open the app and wait until the price stream is connected. */
export async function openApp(page: Page): Promise<void> {
  await page.goto("/");
  await expect(page.getByTestId("connection-status")).toHaveAttribute("data-status", "connected");
}

/** Remove a ticker from the watchlist via the API, ignoring 404. */
export async function ensureNotWatched(request: APIRequestContext, ticker: string): Promise<void> {
  const res = await request.delete(`/api/watchlist/${ticker}`);
  expect([204, 404]).toContain(res.status());
}

/** Current held quantity of a ticker according to the API. */
export async function heldQuantity(request: APIRequestContext, ticker: string): Promise<number> {
  const portfolio = await (await request.get("/api/portfolio")).json();
  const position = portfolio.positions.find((p: { ticker: string }) => p.ticker === ticker);
  return position ? position.quantity : 0;
}

/** Execute a trade via the API and assert it succeeded. */
export async function apiTrade(
  request: APIRequestContext,
  ticker: string,
  side: "buy" | "sell",
  quantity: number,
): Promise<void> {
  const res = await request.post("/api/portfolio/trade", { data: { ticker, side, quantity } });
  expect(res.status(), await res.text()).toBe(200);
}

/** Fill the trade bar and click buy or sell. */
export async function uiTrade(page: Page, ticker: string, side: "buy" | "sell", quantity: number): Promise<void> {
  await page.getByTestId("trade-ticker").fill(ticker);
  await page.getByTestId("trade-quantity").fill(String(quantity));
  await page.getByTestId(`${side}-button`).click();
}
