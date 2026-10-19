"use client";

import {
  AreaSeries,
  CrosshairMode,
  LineStyle,
  createChart,
  type IChartApi,
  type ISeriesApi,
  type UTCTimestamp,
} from "lightweight-charts";
import { useEffect, useRef } from "react";
import { formatPrice } from "@/lib/format";
import type { ChartPoint } from "@/lib/usePriceStream";

const MONO = 'ui-monospace, "SF Mono", Menlo, Consolas, monospace';
const clock = (t: number) => new Date(t * 1000).toLocaleTimeString("en-GB");
const asData = (pts: ChartPoint[]) => pts as { time: UTCTimestamp; value: number }[];

function createAreaChart(container: HTMLElement) {
  const label = { color: "#8b949e", style: LineStyle.Dashed, labelBackgroundColor: "#161b22" };
  const chart = createChart(container, {
    autoSize: true,
    layout: { background: { color: "transparent" }, textColor: "#8b949e", fontSize: 12, fontFamily: MONO },
    grid: { vertLines: { color: "rgba(48,54,61,0.5)" }, horzLines: { color: "rgba(48,54,61,0.5)" } },
    crosshair: { mode: CrosshairMode.Normal, vertLine: label, horzLine: label },
    rightPriceScale: { borderColor: "#30363d", scaleMargins: { top: 0.1, bottom: 0.1 } },
    timeScale: {
      borderColor: "#30363d",
      timeVisible: true,
      secondsVisible: true,
      rightOffset: 4,
      tickMarkFormatter: (t: number) => clock(t),
    },
    localization: {
      timeFormatter: (t: number) => clock(t),
      priceFormatter: (p: number) =>
        "$" + p.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 }),
    },
  });
  const series = chart.addSeries(AreaSeries, {
    lineColor: "#209dd7",
    topColor: "rgba(32,157,215,0.28)",
    bottomColor: "rgba(32,157,215,0)",
    lineWidth: 2,
    priceLineVisible: true,
    lastValueVisible: true,
    crosshairMarkerRadius: 4,
  });
  return { chart, series };
}

export default function MainChart({
  ticker,
  points,
  price,
  live,
}: {
  ticker: string;
  points: ChartPoint[];
  price?: number;
  live: boolean;
}) {
  const host = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Area"> | null>(null);
  const lastTime = useRef(0);
  const shown = useRef("");

  useEffect(() => {
    const { chart, series } = createAreaChart(host.current!);
    chartRef.current = chart;
    seriesRef.current = series;
    return () => {
      chart.remove();
      chartRef.current = null;
      seriesRef.current = null;
      shown.current = "";
      lastTime.current = 0;
    };
  }, []);

  useEffect(() => {
    const series = seriesRef.current!;
    const last = points[points.length - 1];
    if (shown.current !== ticker) {
      shown.current = ticker;
      series.setData(asData(points));
      chartRef.current!.timeScale().fitContent();
      lastTime.current = last?.time ?? 0;
    } else if (last && last.time >= lastTime.current) {
      series.update(asData([last])[0]);
      lastTime.current = last.time;
    }
  }, [ticker, points]);

  return (
    <div data-testid="main-chart" data-ticker={ticker} className="flex h-full flex-col">
      <div className="flex h-10 items-center justify-between border-b border-border bg-surface px-2">
        <span data-testid="main-chart-ticker" className="font-mono text-base font-semibold">
          {ticker}
        </span>
        <span
          data-testid="main-chart-price"
          className={`font-mono text-xl font-semibold tabular-nums ${live ? "" : "text-text-muted"}`}
        >
          {formatPrice(price)}
        </span>
      </div>
      <div className="relative min-h-0 flex-1">
        <div ref={host} className="absolute inset-0" />
        {ticker === "" && (
          <p className="absolute inset-0 flex items-center justify-center text-sm text-text-muted">
            Add a ticker to see its chart.
          </p>
        )}
        {ticker !== "" && points.length < 2 && (
          <div
            data-testid="main-chart-empty"
            role="status"
            className="absolute inset-0 flex flex-col items-center justify-center gap-1 bg-bg text-text-muted"
          >
            <p className="text-sm">Collecting price data for {ticker}...</p>
            <p className="text-xs">The chart fills in as prices stream.</p>
          </div>
        )}
      </div>
    </div>
  );
}
