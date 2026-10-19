const W = 64;

function toPoints(points: number[]) {
  const min = Math.min(...points);
  const max = Math.max(...points);
  const span = max - min;
  return points
    .map((p, i) => {
      const x = (i * W) / (points.length - 1);
      const y = span === 0 ? 10 : 18 - ((p - min) / span) * 16;
      return x.toFixed(1) + "," + y.toFixed(1);
    })
    .join(" ");
}

export default function Sparkline({ points, up }: { points: number[]; up: boolean }) {
  return (
    <svg width="64" height="20" viewBox="0 0 64 20" aria-hidden="true">
      {points.length >= 2 && (
        <polyline
          points={toPoints(points)}
          fill="none"
          stroke={up ? "var(--color-up)" : "var(--color-down)"}
          strokeWidth={1.5}
          strokeLinejoin="round"
          vectorEffect="non-scaling-stroke"
        />
      )}
    </svg>
  );
}
