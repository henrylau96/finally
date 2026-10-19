import { Page, expect, test } from "@playwright/test";
import { ensureNotWatched, heldQuantity, openApp, readNumber } from "./helpers";

async function sendChat(page: Page, text: string): Promise<void> {
  await page.getByTestId("chat-input").fill(text);
  await page.getByTestId("chat-send").click();
  await expect(page.getByTestId("chat-loading")).toHaveCount(0);
}

test("example prompt fills the input without sending", async ({ page }) => {
  await openApp(page);
  const empty = page.getByTestId("chat-empty");
  test.skip((await empty.count()) === 0, "conversation history already exists");
  const before = await page.getByTestId("chat-message").count();
  await page.getByTestId("chat-example").filter({ hasText: "Buy 5 NVDA" }).click();
  await expect(page.getByTestId("chat-input")).toHaveValue("Buy 5 NVDA");
  await expect(page.getByTestId("chat-message")).toHaveCount(before);
});

test("mocked AI chat executes a trade shown inline", async ({ page, request }) => {
  await openApp(page);
  const cash = page.getByTestId("cash-balance");
  const before = await readNumber(cash);
  const heldBefore = await heldQuantity(request, "AAPL");

  await expect(page.getByTestId("chat-panel")).toBeVisible();
  await page.getByTestId("chat-input").fill("buy 1 AAPL");
  await page.getByTestId("chat-send").click();

  await expect(page.locator('[data-testid="chat-message"][data-role="user"]').last()).toContainText("buy 1 AAPL");
  await expect(page.locator('[data-testid="chat-message"][data-role="assistant"]').last()).toContainText(
    "Mock response",
  );
  const action = page.getByTestId("chat-action").last();
  await expect(action).toContainText("AAPL");
  await expect(action).toHaveAttribute("data-ok", "true");
  await expect(page.getByTestId("chat-loading")).toHaveCount(0);

  await expect.poll(() => readNumber(cash)).toBeLessThan(before);
  expect(await heldQuantity(request, "AAPL")).toBeCloseTo(heldBefore + 1);
});

test("chat watchlist add shows a chip and updates the watchlist", async ({ page, request }) => {
  await ensureNotWatched(request, "SHOP");
  await openApp(page);
  await sendChat(page, "add SHOP");
  const chip = page.getByTestId("chat-action").last();
  await expect(chip).toHaveAttribute("data-type", "watchlist");
  await expect(chip).toHaveAttribute("data-ok", "true");
  await expect(chip).toContainText("Added SHOP");
  await expect(page.getByTestId("watchlist-row-SHOP")).toBeVisible();

  await sendChat(page, "remove SHOP");
  await expect(page.getByTestId("chat-action").last()).toContainText("Removed SHOP");
  await expect(page.getByTestId("watchlist-row-SHOP")).toHaveCount(0);
});

test("failed AI trade shows the server reason", async ({ page }) => {
  await openApp(page);
  const cash = page.getByTestId("cash-balance");
  const before = await readNumber(cash);
  await sendChat(page, "buy 100000 NFLX");
  const chip = page.getByTestId("chat-action").last();
  await expect(chip).toHaveAttribute("data-ok", "false");
  await expect(chip).toContainText("Insufficient cash");
  expect(await readNumber(cash)).toBe(before);
});

test("history survives reload", async ({ page }) => {
  await openApp(page);
  await sendChat(page, "How is my portfolio doing?");
  await page.reload();
  await expect(page.getByTestId("connection-status")).toHaveAttribute("data-status", "connected");
  await expect(
    page.locator('[data-testid="chat-message"][data-role="user"]').filter({ hasText: "How is my portfolio doing?" }).last(),
  ).toBeVisible();
});

test("input is disabled while a reply is pending", async ({ page }) => {
  await openApp(page);
  await page.getByTestId("chat-input").fill("hello there");
  await page.getByTestId("chat-send").click();
  await expect(page.getByTestId("chat-send")).toBeDisabled();
  await expect(page.getByTestId("chat-loading")).toHaveCount(0);
  await expect(page.getByTestId("chat-input")).toBeEnabled();
});
