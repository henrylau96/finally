"use client";

import { useEffect, useRef } from "react";
import { createChart, LineSeries, type IChartApi, type ISeriesApi, type UTCTimestamp } from "lightweight-charts";
import { chartOptions } from "@/lib/chartTheme";
import { toChartPoints } from "@/lib/prices";
import type { Snapshot } from "@/lib/types";

/** Line chart of total portfolio value from recorded snapshots. */
export function PnlChart({ snapshots }: { snapshots: Snapshot[] }) {
  const container = useRef<HTMLDivElement>(null);
  const chart = useRef<IChartApi | null>(null);
  const series = useRef<ISeriesApi<"Line"> | null>(null);

  useEffect(() => {
    chart.current = createChart(container.current!, {
      ...chartOptions,
      timeScale: { ...chartOptions.timeScale, secondsVisible: false },
    });
    series.current = chart.current.addSeries(LineSeries, { color: "#ecad0a", lineWidth: 2 });
    return () => chart.current?.remove();
  }, []);

  useEffect(() => {
    const points = toChartPoints(
      snapshots.map((s) => ({ time: Date.parse(s.recorded_at) / 1000, value: s.total_value })),
    );
    series.current?.setData(points.map((p) => ({ time: p.time as UTCTimestamp, value: p.value })));
    chart.current?.timeScale().fitContent();
  }, [snapshots]);

  return (
    <section className="flex min-h-0 flex-col bg-panel">
      <h2 className="px-3 pt-2.5 pb-1.5 text-xs font-medium text-muted">Portfolio value</h2>
      <div
        data-testid="pnl-chart"
        data-points={snapshots.length}
        ref={container}
        className="mx-1 mb-1 min-h-0 flex-1"
      />
    </section>
  );
}
