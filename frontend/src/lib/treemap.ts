export interface TreemapItem {
  key: string;
  value: number;
}

export interface TreemapRect extends TreemapItem {
  x: number;
  y: number;
  w: number;
  h: number;
}

/**
 * Lay out items in a unit square (0..1) with a squarified treemap.
 * Rectangle areas are proportional to item values.
 */
export function squarify(items: TreemapItem[]): TreemapRect[] {
  const total = items.reduce((s, i) => s + i.value, 0);
  if (total <= 0) return [];
  const sorted = [...items].filter((i) => i.value > 0).sort((a, b) => b.value - a.value);
  const scaled = sorted.map((i) => ({ ...i, area: i.value / total }));
  const out: TreemapRect[] = [];
  let box = { x: 0, y: 0, w: 1, h: 1 };
  let row: typeof scaled = [];

  const worst = (r: typeof scaled, side: number) => {
    const sum = r.reduce((s, i) => s + i.area, 0);
    const max = Math.max(...r.map((i) => i.area));
    const min = Math.min(...r.map((i) => i.area));
    return Math.max((side * side * max) / (sum * sum), (sum * sum) / (side * side * min));
  };

  const placeRow = (r: typeof scaled) => {
    const sum = r.reduce((s, i) => s + i.area, 0);
    const horizontal = box.w >= box.h;
    const thickness = horizontal ? sum / box.h : sum / box.w;
    let offset = 0;
    for (const i of r) {
      const len = i.area / thickness;
      out.push(
        horizontal
          ? { key: i.key, value: i.value, x: box.x, y: box.y + offset, w: thickness, h: len }
          : { key: i.key, value: i.value, x: box.x + offset, y: box.y, w: len, h: thickness },
      );
      offset += len;
    }
    box = horizontal
      ? { x: box.x + thickness, y: box.y, w: box.w - thickness, h: box.h }
      : { x: box.x, y: box.y + thickness, w: box.w, h: box.h - thickness };
  };

  for (const item of scaled) {
    const side = Math.min(box.w, box.h);
    if (row.length === 0 || worst([...row, item], side) <= worst(row, side)) {
      row.push(item);
    } else {
      placeRow(row);
      row = [item];
    }
  }
  if (row.length) placeRow(row);
  return out;
}
