import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { useHistorySeeds } from "./useHistorySeeds";

const pts = (v: number) => [{ time: 1, value: v }];
const ok = (v: number) => ({ ok: true, json: async () => pts(v) });

afterEach(() => vi.unstubAllGlobals());

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

  it("stores [] on a non-ok response and moves on", async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce({ ok: false }).mockResolvedValueOnce(ok(2));
    vi.stubGlobal("fetch", fetchMock);
    const { result } = renderHook(() => useHistorySeeds(["AAPL", "MSFT"]));
    await waitFor(() => expect(result.current).toEqual({ AAPL: [], MSFT: pts(2) }));
    expect(fetchMock).toHaveBeenCalledTimes(2);
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
