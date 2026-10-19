export type Rect = { id: string; x: number; y: number; w: number; h: number };

function worst(row: number[], side: number): number {
  const s = row.reduce((a, b) => a + b, 0);
  return Math.max((side * side * Math.max(...row)) / (s * s), (s * s) / (side * side * Math.min(...row)));
}

/**
 * Squarified treemap (Bruls, Huizing, van Wijk 2000).
 * Items with value <= 0 are dropped; returns one rect per item, largest first.
 */
export function squarify(items: { id: string; value: number }[], width: number, height: number): Rect[] {
  const sorted = items.filter((i) => i.value > 0).sort((a, b) => b.value - a.value);
  const total = sorted.reduce((s, i) => s + i.value, 0);
  if (total === 0 || width <= 0 || height <= 0) return [];
  const k = (width * height) / total;
  const out: Rect[] = [];
  let x = 0;
  let y = 0;
  let w = width;
  let h = height;
  let i = 0;
  while (i < sorted.length) {
    const side = Math.min(w, h);
    const row = [sorted[i].value * k];
    let j = i + 1;
    while (j < sorted.length && worst([...row, sorted[j].value * k], side) <= worst(row, side)) {
      row.push(sorted[j++].value * k);
    }
    const s = row.reduce((a, b) => a + b, 0);
    if (w >= h) {
      const cw = s / h;
      let yy = y;
      row.forEach((a, n) => {
        out.push({ id: sorted[i + n].id, x, y: yy, w: cw, h: a / cw });
        yy += a / cw;
      });
      x += cw;
      w -= cw;
    } else {
      const rh = s / w;
      let xx = x;
      row.forEach((a, n) => {
        out.push({ id: sorted[i + n].id, x: xx, y, w: a / rh, h: rh });
        xx += a / rh;
      });
      y += rh;
      h -= rh;
    }
    i = j;
  }
  return out;
}
