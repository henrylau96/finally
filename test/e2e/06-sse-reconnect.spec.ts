import { expect, test } from "@playwright/test";

/**
 * Chromium's offline emulation does not cut an already-open SSE stream, so the stream
 * is blocked from page load instead; EventSource retries until it is unblocked.
 */
test("connection status recovers after the stream is unblocked", async ({ page }) => {
  let blocked = 0;
  await page.route("**/api/stream/prices", (route) => {
    blocked += 1;
    return route.abort();
  });
  await page.goto("/");
  const status = page.getByTestId("connection-status");
  await expect.poll(() => blocked, { timeout: 15_000 }).toBeGreaterThanOrEqual(2);
  await expect(status).toHaveAttribute("data-status", "reconnecting");

  await page.unroute("**/api/stream/prices");
  await expect(status).toHaveAttribute("data-status", "connected", { timeout: 20_000 });

  const price = page.getByTestId("price-AAPL");
  await expect.poll(() => price.textContent(), { timeout: 15_000 }).toMatch(/\d/);
  const first = await price.textContent();
  await expect.poll(() => price.textContent(), { timeout: 15_000 }).not.toBe(first);
});
