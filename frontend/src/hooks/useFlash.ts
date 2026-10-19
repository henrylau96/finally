"use client";

import { useEffect, useState } from "react";

export type FlashClass = "" | "flash-up" | "flash-down";

/** Return a flash class for a brief moment whenever `value` changes. */
export function useFlash(value: number | null | undefined, holdMs = 60): FlashClass {
  const [prev, setPrev] = useState(value);
  const [flash, setFlash] = useState<FlashClass>("");

  if (value !== prev) {
    setPrev(value);
    if (value != null && prev != null) setFlash(value > prev ? "flash-up" : "flash-down");
  }

  useEffect(() => {
    if (!flash) return;
    const id = setTimeout(() => setFlash(""), holdMs);
    return () => clearTimeout(id);
  }, [flash, value, holdMs]);

  return flash;
}
