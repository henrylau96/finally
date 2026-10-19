import { describe, expect, it } from "vitest";
import { squarify } from "./treemap";

describe("squarify", () => {
  it("returns rects whose areas match value weights", () => {
    const rects = squarify([
      { key: "A", value: 6 },
      { key: "B", value: 3 },
      { key: "C", value: 1 },
    ]);
    expect(rects).toHaveLength(3);
    const area = (k: string) => {
      const r = rects.find((x) => x.key === k)!;
      return r.w * r.h;
    };
    expect(area("A")).toBeCloseTo(0.6);
    expect(area("B")).toBeCloseTo(0.3);
    expect(area("C")).toBeCloseTo(0.1);
  });

  it("returns nothing for empty input", () => {
    expect(squarify([])).toEqual([]);
  });
});
