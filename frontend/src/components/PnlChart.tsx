"use client";

import { LineSeries, LineStyle, type IChartApi, type ISeriesApi } from "lightweight-charts";
import { useEffect, useRef, useState } from "react";
import { CHART, createBaseChart } from "@/lib/chartTheme";
import { toSeries } from "@/lib/portfolio";
import Panel from "./Panel";

export default function PnlChart({ version }: { version: number }) {
  const host = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<"Line"> | null>(null);
  const fitted = useRef(false);
  const seq = useRef(0);
  const [count, setCount] = useState(0);

  useEffect(() => {
    const chart = createBaseChart(host.current!, { secondsVisible: false });
    const series = chart.addSeries(LineSeries, {
      color: CHART.primary,
      lineWidth: 2,
      lastValueVisible: true,
      priceLineVisible: false,
      crosshairMarkerRadius: 4,
    });
    series.createPriceLine({
      price: 10000,
      color: CHART.muted,
      lineStyle: LineStyle.Dashed,
      lineWidth: 1,
      axisLabelVisible: false,
      title: "",
    });
    chartRef.current = chart;
    seriesRef.current = series;
    return () => {
      chart.remove();
      chartRef.current = null;
      seriesRef.current = null;
      fitted.current = false;
    };
  }, []);

  useEffect(() => {
    async function load() {
      const mine = ++seq.current;
      try {
        const r = await fetch("/api/portfolio/history");
        if (!r.ok) return;
        const data = toSeries(await r.json());
        if (mine !== seq.current || !seriesRef.current) return;
        seriesRef.current.setData(data);
        seriesRef.current.applyOptions({ pointMarkersVisible: data.length === 1 });
        if (data.length > 0 && !fitted.current) {
          fitted.current = true;
          chartRef.current!.timeScale().fitContent();
        }
        setCount(data.length);
      } catch {
        // keep previous data
      }
    }
    void load();
    const id = setInterval(load, 30_000);
    return () => clearInterval(id);
  }, [version]);

  return (
    <Panel title="P&L" testId="pnl-chart" data-points={count} bodyClassName="overflow-hidden">
      <div className="relative h-full">
        <div ref={host} className="absolute inset-0" />
        {count === 0 && (
          <div
            data-testid="pnl-empty"
            role="status"
            className="absolute inset-0 flex flex-col items-center justify-center gap-1 bg-bg text-text-muted"
          >
            <p className="text-sm">No portfolio history yet.</p>
            <p className="text-xs">The chart fills in as snapshots are recorded.</p>
          </div>
        )}
      </div>
    </Panel>
  );
}
