"use client";

import { useEffect, useRef } from "react";
import { AreaSeries, createChart, type IChartApi, type ISeriesApi, type UTCTimestamp } from "lightweight-charts";
import { chartOptions } from "@/lib/chartTheme";
import { price } from "@/lib/format";
import { toChartPoints } from "@/lib/prices";
import type { PricePoint } from "@/lib/types";

interface Props {
  ticker: string;
  points: PricePoint[];
}

const asData = (pts: PricePoint[]) => pts.map((p) => ({ time: p.time as UTCTimestamp, value: p.value }));

/** Large live chart of the selected ticker's streamed prices. */
export function PriceChart({ ticker, points }: Props) {
  const container = useRef<HTMLDivElement>(null);
  const chart = useRef<IChartApi | null>(null);
  const series = useRef<ISeriesApi<"Area"> | null>(null);
  const shownTicker = useRef("");

  useEffect(() => {
    chart.current = createChart(container.current!, chartOptions);
    series.current = chart.current.addSeries(AreaSeries, {
      lineColor: "#209dd7",
      lineWidth: 2,
      topColor: "rgba(32, 157, 215, 0.28)",
      bottomColor: "rgba(32, 157, 215, 0.02)",
    });
    return () => chart.current?.remove();
  }, []);

  useEffect(() => {
    const data = asData(toChartPoints(points));
    if (shownTicker.current !== ticker) {
      series.current?.setData(data);
      shownTicker.current = ticker;
    } else if (data.length) {
      series.current?.update(data[data.length - 1]);
    }
    chart.current?.timeScale().fitContent();
  }, [ticker, points]);

  const last = points[points.length - 1]?.value;
  return (
    <section data-testid="main-chart" data-ticker={ticker} className="flex min-h-0 flex-1 flex-col">
      <div className="flex items-baseline gap-3 px-3 pt-2.5 pb-1">
        <h2 className="text-base font-semibold text-accent">{ticker || "Select a ticker"}</h2>
        {last != null && <span className="num text-base">{price(last)}</span>}
        <span className="text-xs text-muted">Since page load</span>
      </div>
      <div ref={container} className="min-h-0 flex-1" />
    </section>
  );
}
