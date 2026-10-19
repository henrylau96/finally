import type { PricePoint } from "@/lib/types";

interface Props {
  points: PricePoint[];
  width?: number;
  height?: number;
  color: string;
}

/** Tiny SVG line of recent prices. */
export function Sparkline({ points, width = 64, height = 22, color }: Props) {
  if (points.length < 2) return <svg width={width} height={height} aria-hidden />;
  const values = points.map((p) => p.value);
  const min = Math.min(...values);
  const span = Math.max(...values) - min || 1;
  const step = width / (points.length - 1);
  const d = values
    .map((v, i) => `${(i * step).toFixed(1)},${(height - 1 - ((v - min) / span) * (height - 2)).toFixed(1)}`)
    .join(" ");
  return (
    <svg width={width} height={height} aria-hidden>
      <polyline points={d} fill="none" stroke={color} strokeWidth={1.25} />
    </svg>
  );
}
