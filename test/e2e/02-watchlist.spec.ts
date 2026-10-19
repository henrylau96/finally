import { expect, test } from "@playwright/test";
import { ensureNotWatched, openApp, readNumber } from "./helpers";

const TICKER = "PYPL";

test("add and remove a ticker from the watchlist", async ({ page, request }) => {
  await ensureNotWatched(request, TICKER);
  await openApp(page);
  const row = page.getByTestId(`watchlist-row-${TICKER}`);
  await expect(row).toHaveCount(0);

  await page.getByTestId("watchlist-add-input").fill(TICKER.toLowerCase());
  await page.getByTestId("watchlist-add-button").click();
  await expect(row).toBeVisible();
  await expect.poll(() => readNumber(page.getByTestId(`price-${TICKER}`)), { timeout: 15_000 }).toBeGreaterThan(0);

  await page.getByTestId(`watchlist-remove-${TICKER}`).click();
  await expect(row).toHaveCount(0);

  const tickers = (await (await request.get("/api/watchlist")).json()).map((w: { ticker: string }) => w.ticker);
  expect(tickers).not.toContain(TICKER);
});

test("clicking a ticker selects it in the main chart", async ({ page }) => {
  await openApp(page);
  await page.getByTestId("watchlist-row-MSFT").click();
  await expect(page.getByTestId("main-chart")).toHaveAttribute("data-ticker", "MSFT");
});
