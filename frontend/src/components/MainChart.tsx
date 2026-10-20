"use client";

import {
  AreaSeries,
  type IChartApi,
  type ISeriesApi,
  type UTCTimestamp,
} from "lightweight-charts";
import { useEffect, useMemo, useRef } from "react";
import { CHART, createBaseChart } from "@/lib/chartTheme";
import { mergePoints } from "@/lib/chartPoints";
import { formatPrice } from "@/lib/format";
import type { ChartPoint } from "@/lib/usePriceStream";

const asData = (pts: ChartPoint[]) => pts as { time: UTCTimestamp; value: number }[];

function createAreaChart(container: HTMLElement) {
  const chart = createBaseChart(container, { secondsVisible: true });
  const series = chart.addSeries(AreaSeries, {
    lineColor: CHART.primary,
    topColor: CHART.primaryFill,
    bottomColor: CHART.primaryFillEnd,
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
  history,
  price,
  live,
}: {
  ticker: string;
  points: ChartPoint[];
  history: ChartPoint[];
  price?: number;
  live: boolean;
}) {
  const host = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Area"> | null>(null);
  const lastTime = useRef(0);
  const shown = useRef("");
  const shownHistory = useRef<ChartPoint[] | null>(null);
  const merged = useMemo(() => mergePoints(history, points), [history, points]);

  useEffect(() => {
    const { chart, series } = createAreaChart(host.current!);
    chartRef.current = chart;
    seriesRef.current = series;
    return () => {
      chart.remove();
      chartRef.current = null;
      seriesRef.current = null;
      shown.current = "";
      shownHistory.current = null;
      lastTime.current = 0;
    };
  }, []);

  useEffect(() => {
    const series = seriesRef.current!;
    const last = merged[merged.length - 1];
    if (shown.current !== ticker || shownHistory.current !== history) {
      shown.current = ticker;
      shownHistory.current = history;
      series.setData(asData(merged));
      chartRef.current!.timeScale().fitContent();
      lastTime.current = last?.time ?? 0;
    } else if (last && last.time >= lastTime.current) {
      series.update(asData([last])[0]);
      lastTime.current = last.time;
    }
  }, [ticker, history, merged]);

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
        {ticker !== "" && merged.length < 2 && (
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
