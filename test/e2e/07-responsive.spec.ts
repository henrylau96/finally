import { Page, expect, test } from "@playwright/test";
import { openApp } from "./helpers";

async function noHorizontalScroll(page: Page): Promise<void> {
  const over = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(over).toBeLessThanOrEqual(0);
}

async function noVerticalScroll(page: Page): Promise<void> {
  const over = await page.evaluate(() => document.documentElement.scrollHeight - window.innerHeight);
  expect(over).toBeLessThanOrEqual(0);
}

async function panelsVisible(page: Page): Promise<void> {
  for (const id of ["app-header", "watchlist", "main-chart", "chat-panel"]) {
    await expect(page.getByTestId(id)).toBeVisible();
  }
}

for (const width of [1600, 1280]) {
  test(`desktop layout at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    await openApp(page);
    await panelsVisible(page);
    await expect(page.getByTestId("chat-panel")).toHaveAttribute("data-collapsed", "false");
    await noHorizontalScroll(page);
    await noVerticalScroll(page);
  });
}

async function checkDockOverlay(page: Page): Promise<void> {
  const panel = page.getByTestId("chat-panel");
  await expect(panel).toHaveAttribute("data-collapsed", "true");
  await page.getByTestId("chat-toggle").click();
  await expect(panel).toHaveAttribute("data-collapsed", "false");
  await expect(page.getByTestId("chat-input")).toBeVisible();
  await noHorizontalScroll(page);
  await page.getByTestId("chat-toggle").click();
  await expect(panel).toHaveAttribute("data-collapsed", "true");
}

test("tablet layout at 1024px", async ({ page }) => {
  await page.setViewportSize({ width: 1024, height: 900 });
  await openApp(page);
  await panelsVisible(page);
  await noHorizontalScroll(page);
  await noVerticalScroll(page);
  await checkDockOverlay(page);
});

test("tablet layout at 768px", async ({ page }) => {
  await page.setViewportSize({ width: 768, height: 900 });
  await openApp(page);
  await panelsVisible(page);
  await noHorizontalScroll(page);
  const positions = await page.getByTestId("positions").boundingBox();
  const heatmap = await page.getByTestId("heatmap").boundingBox();
  expect(positions!.width).toBeGreaterThan(heatmap!.width);
  await checkDockOverlay(page);
});
