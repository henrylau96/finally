import { expect, test } from "@playwright/test";
import { apiTrade, openApp } from "./helpers";

test("heatmap and P&L chart render with data", async ({ page, request }) => {
  await apiTrade(request, "NVDA", "buy", 1);
  const history = await (await request.get("/api/portfolio/history")).json();
  expect(history.length).toBeGreaterThan(0);

  await openApp(page);
  const cell = page.getByTestId("heatmap-cell-NVDA");
  await expect(page.getByTestId("heatmap")).toBeVisible();
  await expect(cell).toBeVisible();
  await expect(cell).toHaveAttribute("data-pnl", /^(positive|negative|flat)$/);

  await expect(cell).toHaveAttribute("role", "button");
  await cell.click();
  await expect(cell).toHaveAttribute("aria-pressed", "true");
  await expect(cell).toHaveAttribute("data-selected", "true");

  const pnlChart = page.getByTestId("pnl-chart");
  await expect(pnlChart).toBeVisible();
  await expect(pnlChart.locator("canvas, svg").first()).toBeVisible();
  await expect.poll(async () => Number(await pnlChart.getAttribute("data-points"))).toBeGreaterThan(0);
});
