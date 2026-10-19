import { expect, test } from "@playwright/test";
import { apiTrade, heldQuantity, openApp, readNumber, uiTrade } from "./helpers";

test("buy shares: cash decreases and position appears", async ({ page, request }) => {
  await openApp(page);
  const cash = page.getByTestId("cash-balance");
  const before = await readNumber(cash);
  const heldBefore = await heldQuantity(request, "AAPL");

  await uiTrade(page, "AAPL", "buy", 2);

  await expect.poll(() => readNumber(cash)).toBeLessThan(before);
  await expect(page.getByTestId("position-row-AAPL")).toBeVisible();
  expect(await heldQuantity(request, "AAPL")).toBeCloseTo(heldBefore + 2);
});

test("sell shares: cash increases, position updates then disappears", async ({ page, request }) => {
  await apiTrade(request, "MSFT", "buy", 3);
  await openApp(page);
  const cash = page.getByTestId("cash-balance");
  const row = page.getByTestId("position-row-MSFT");
  await expect(row).toBeVisible();

  const before = await readNumber(cash);
  const held = await heldQuantity(request, "MSFT");
  await uiTrade(page, "MSFT", "sell", 1);
  await expect.poll(() => readNumber(cash)).toBeGreaterThan(before);
  await expect.poll(() => heldQuantity(request, "MSFT")).toBeCloseTo(held - 1);
  await expect(row).toBeVisible();

  await uiTrade(page, "MSFT", "sell", held - 1);
  await expect(row).toHaveCount(0);
  expect(await heldQuantity(request, "MSFT")).toBe(0);
});

test("selling more than owned shows an error", async ({ page, request }) => {
  await openApp(page);
  const held = await heldQuantity(request, "NFLX");
  const cash = page.getByTestId("cash-balance");
  const before = await readNumber(cash);

  await uiTrade(page, "NFLX", "sell", held + 1000);

  await expect(page.getByTestId("trade-error")).toBeVisible();
  expect(await readNumber(cash)).toBe(before);
});
