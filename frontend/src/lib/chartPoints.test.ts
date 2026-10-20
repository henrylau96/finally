import { describe, expect, it } from "vitest";
import { mergePoints } from "./chartPoints";

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
