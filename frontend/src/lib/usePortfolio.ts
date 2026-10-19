"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { Portfolio } from "./portfolio";

export function usePortfolio() {
  const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
  const [version, setVersion] = useState(0);
  const seq = useRef(0);

  const refresh = useCallback(async () => {
    const id = ++seq.current;
    let data: Portfolio | null = null;
    try {
      const res = await fetch("/api/portfolio");
      if (res.ok) data = await res.json();
    } catch {}
    if (id !== seq.current || !data) return;
    setPortfolio(data);
    setVersion((v) => v + 1);
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return { portfolio, version, refresh };
}
