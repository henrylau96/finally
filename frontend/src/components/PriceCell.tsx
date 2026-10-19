"use client";

import { useEffect, useRef } from "react";
import { formatPrice } from "@/lib/format";
import type { Quote } from "@/lib/usePriceStream";

export default function PriceCell({
  ticker,
  price,
  direction,
  live,
}: {
  ticker: string;
  price?: number;
  direction?: Quote["direction"];
  live: boolean;
}) {
  const ref = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.removeAttribute("data-flash");
    if (!live || (direction !== "up" && direction !== "down")) return;
    void el.offsetWidth;
    el.setAttribute("data-flash", direction);
    let inner = 0;
    const outer = requestAnimationFrame(() => {
      inner = requestAnimationFrame(() => el.removeAttribute("data-flash"));
    });
    return () => {
      cancelAnimationFrame(outer);
      cancelAnimationFrame(inner);
    };
  }, [price, direction, live]);

  return (
    <span
      ref={ref}
      data-testid={"price-" + ticker}
      className={"price-cell px-1 font-mono " + (live ? "text-text" : "text-text-muted")}
    >
      {formatPrice(price)}
    </span>
  );
}
