import { expect, test } from "@playwright/test";
import { heldQuantity, openApp, readNumber } from "./helpers";

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
