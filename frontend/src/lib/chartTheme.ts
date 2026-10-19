import { ColorType, type DeepPartial, type ChartOptions } from "lightweight-charts";

/** Shared dark styling for lightweight-charts instances. */
export const chartOptions: DeepPartial<ChartOptions> = {
  autoSize: true,
  layout: {
    background: { type: ColorType.Solid, color: "#131a25" },
    textColor: "#7d8899",
    fontFamily: "var(--font-plex-mono), monospace",
    fontSize: 11,
    attributionLogo: false,
  },
  grid: {
    vertLines: { color: "#1c2636" },
    horzLines: { color: "#1c2636" },
  },
  rightPriceScale: { borderColor: "#253246" },
  timeScale: { borderColor: "#253246", timeVisible: true, secondsVisible: true },
  crosshair: { horzLine: { labelBackgroundColor: "#209dd7" }, vertLine: { labelBackgroundColor: "#209dd7" } },
};
