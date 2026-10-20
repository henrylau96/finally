import { CrosshairMode, LineStyle, TickMarkType, createChart, type IChartApi } from "lightweight-charts";

export const CHART = {
  text: "#8b949e",
  grid: "rgba(48,54,61,0.5)",
  border: "#30363d",
  labelBg: "#161b22",
  primary: "#209dd7",
  primaryFill: "rgba(32,157,215,0.28)",
  primaryFillEnd: "rgba(32,157,215,0)",
  muted: "#8b949e",
};

export const MONO = 'ui-monospace, "SF Mono", Menlo, Consolas, monospace';
const NY = { timeZone: "America/New_York" } as const;
export const day = (t: number) => new Date(t * 1000).toLocaleDateString("en-GB", { ...NY, day: "2-digit", month: "short" });
export const clock = (t: number) => new Date(t * 1000).toLocaleTimeString("en-GB", NY);
const year = (t: number) => new Date(t * 1000).toLocaleDateString("en-GB", { ...NY, year: "numeric" });

/** Axis label in exchange (New York) time: year, day, or clock by tick type. */
export function tickLabel(t: number, type: TickMarkType): string {
  if (type === TickMarkType.Year) return year(t);
  return type < TickMarkType.Time ? day(t) : clock(t);
}

/** Crosshair label: exchange date and time. */
export const crosshairLabel = (t: number) => day(t) + " " + clock(t);

/** Create a dark-themed chart shared by the main chart and the P&L chart. */
export function createBaseChart(container: HTMLElement, opts: { secondsVisible: boolean }): IChartApi {
  const label = { color: CHART.text, style: LineStyle.Dashed, labelBackgroundColor: CHART.labelBg };
  return createChart(container, {
    autoSize: true,
    layout: { background: { color: "transparent" }, textColor: CHART.text, fontSize: 12, fontFamily: MONO },
    grid: { vertLines: { color: CHART.grid }, horzLines: { color: CHART.grid } },
    crosshair: { mode: CrosshairMode.Normal, vertLine: label, horzLine: label },
    rightPriceScale: { borderColor: CHART.border, scaleMargins: { top: 0.1, bottom: 0.1 } },
    timeScale: {
      borderColor: CHART.border,
      timeVisible: true,
      secondsVisible: opts.secondsVisible,
      rightOffset: 4,
      tickMarkFormatter: tickLabel,
    },
    localization: {
      timeFormatter: crosshairLabel,
      priceFormatter: (p: number) =>
        "$" + p.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 }),
    },
  });
}
