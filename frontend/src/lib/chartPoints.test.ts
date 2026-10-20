import { describe, expect, it } from "vitest";
import { mergePoints, sparklineValues } from "./chartPoints";

const p = (time: number, value: number) => ({ time, value });

describe("mergePoints", () => {
  it("returns live when history is empty", () => {
    const live = [p(1, 1)];
    expect(mergePoints([], live)).toBe(live);
  });

  it("returns history when live is empty", () => {
    expect(mergePoints([p(1, 1)], [])).toEqual([p(1, 1)]);
  });

  it("appends live after history", () => {
    expect(mergePoints([p(100, 1), p(200, 2)], [p(300, 3)])).toEqual([p(100, 1), p(200, 2), p(300, 3)]);
  });

  it("drops live points older than history", () => {
    expect(mergePoints([p(100, 1), p(200, 2)], [p(150, 9), p(250, 3)])).toEqual([p(100, 1), p(200, 2), p(250, 3)]);
  });

  it("replaces the last history point on equal time", () => {
    expect(mergePoints([p(100, 1), p(200, 2)], [p(200, 5), p(300, 6)])).toEqual([p(100, 1), p(200, 5), p(300, 6)]);
  });
});

describe("sparklineValues", () => {
  const seed = (n: number) => Array.from({ length: n }, (_, i) => p(100 + i, i));

  it("returns ticks unchanged when seed is empty", () => {
    const ticks = [1, 2];
    expect(sparklineValues([], [p(1, 1)], ticks)).toBe(ticks);
  });

  it("uses the last 30 seed values", () => {
    const out = sparklineValues(seed(40), [], []);
    expect(out).toHaveLength(30);
    expect(out[0]).toBe(10);
    expect(out[29]).toBe(39);
  });

  it("replaces the last close with a same-time live point", () => {
    const out = sparklineValues(seed(30), [p(129, 500)], [500]);
    expect(out).toHaveLength(30);
    expect(out[29]).toBe(500);
  });

  it("appends live values and caps at 120", () => {
    const live = Array.from({ length: 200 }, (_, i) => p(1000 + i, 1000 + i));
    const out = sparklineValues(seed(30), live, []);
    expect(out).toHaveLength(120);
    expect(out[119]).toBe(1199);
  });
});
