import type { NextConfig } from "next";
import { PHASE_DEVELOPMENT_SERVER } from "next/constants";

export default function config(phase: string): NextConfig {
  if (phase === PHASE_DEVELOPMENT_SERVER) {
    return {
      async rewrites() {
        return [{ source: "/api/:path*", destination: "http://localhost:8000/api/:path*" }];
      },
    };
  }
  return { output: "export" };
}
