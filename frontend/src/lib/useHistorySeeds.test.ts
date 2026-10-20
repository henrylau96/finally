import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { RETRY_MS, useHistorySeeds } from "./useHistorySeeds";

const pts = (v: number) => [{ time: 1, value: v }];
const ok = (v: number) => ({ ok: true, json: async () => pts(v) });

afterEach(() => {
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

describe("useHistorySeeds", () => {
  it("fetches one ticker at a time", async () => {
    let resolveA!: (r: unknown) => void;
    const fetchMock = vi
      .fn()
      .mockReturnValueOnce(new Promise((r) => (resolveA = r)))
      .mockResolvedValueOnce(ok(2));
    vi.stubGlobal("fetch", fetchMock);
    const { result } = renderHook(() => useHistorySeeds(["AAPL", "MSFT"]));
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock).toHaveBeenCalledWith("/api/history/AAPL");
    await act(async () => resolveA(ok(1)));
    await waitFor(() => expect(result.current).toEqual({ AAPL: pts(1), MSFT: pts(2) }));
    expect(fetchMock.mock.calls.map((c) => c[0])).toEqual(["/api/history/AAPL", "/api/history/MSFT"]);
  });

  it("skips a failed ticker without storing it, then retries it after RETRY_MS", async () => {
    vi.useFakeTimers();
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({ ok: false })
      .mockResolvedValueOnce(ok(2))
      .mockResolvedValueOnce(ok(1));
    vi.stubGlobal("fetch", fetchMock);
    const { result } = renderHook(() => useHistorySeeds(["AAPL", "MSFT"]));
    await act(() => vi.advanceTimersByTimeAsync(0));
    expect(result.current).toEqual({ MSFT: pts(2) });
    await act(() => vi.advanceTimersByTimeAsync(RETRY_MS));
    expect(result.current).toEqual({ AAPL: pts(1), MSFT: pts(2) });
    expect(fetchMock.mock.calls.map((c) => c[0])).toEqual([
      "/api/history/AAPL",
      "/api/history/MSFT",
      "/api/history/AAPL",
    ]);
  });

  it("requests only the added ticker on rerender", async () => {
    const fetchMock = vi.fn().mockResolvedValue(ok(1));
    vi.stubGlobal("fetch", fetchMock);
    const { result, rerender } = renderHook(({ t }) => useHistorySeeds(t), { initialProps: { t: ["AAPL", "MSFT"] } });
    await waitFor(() => expect(Object.keys(result.current)).toHaveLength(2));
    rerender({ t: ["AAPL", "MSFT", "PYPL"] });
    await waitFor(() => expect(Object.keys(result.current)).toHaveLength(3));
    expect(fetchMock.mock.calls.map((c) => c[0])).toEqual(["/api/history/AAPL", "/api/history/MSFT", "/api/history/PYPL"]);
  });
});
