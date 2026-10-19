import { expect, test } from "@playwright/test";
import { openApp, readNumber } from "./helpers";

const DEFAULT_TICKERS = ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA", "NVDA", "META", "JPM", "V", "NFLX"];

test("health endpoint responds ok", async ({ request }) => {
  const res = await request.get("/api/health");
  expect(res.status()).toBe(200);
  expect(await res.json()).toEqual({ status: "ok" });
});

test("fresh start shows default watchlist and $10,000 cash", async ({ page }) => {
  await openApp(page);
  for (const ticker of DEFAULT_TICKERS) {
    await expect(page.getByTestId(`watchlist-row-${ticker}`)).toBeVisible();
  }
  await expect.poll(() => readNumber(page.getByTestId("cash-balance"))).toBe(10000);
  await expect.poll(() => readNumber(page.getByTestId("total-value"))).toBe(10000);
});

test("prices stream and update", async ({ page }) => {
  await openApp(page);
  const price = page.getByTestId("price-AAPL");
  await expect.poll(() => readNumber(price)).toBeGreaterThan(0);
  const first = await price.textContent();
  await expect.poll(() => price.textContent(), { timeout: 15_000 }).not.toBe(first);
});
