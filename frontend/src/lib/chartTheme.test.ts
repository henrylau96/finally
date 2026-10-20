import { TickMarkType } from "lightweight-charts";
import { describe, expect, it } from "vitest";
import { crosshairLabel, tickLabel } from "./chartTheme";

const T = 1760407200; // 2025-10-14T02:00Z = 13 Oct 22:00 in New York

describe("chart time labels", () => {
  it("formats days in New York time, whatever the local zone", () => {
    expect(tickLabel(T, TickMarkType.DayOfMonth)).toBe("13 Oct");
  });

  it("shows the year on year ticks", () => {
    expect(tickLabel(T, TickMarkType.Year)).toBe("2025");
  });

  it("includes the date in the crosshair label", () => {
    expect(crosshairLabel(T)).toBe("13 Oct 22:00:00");
  });
});
