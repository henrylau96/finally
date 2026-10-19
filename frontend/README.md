# FinAlly Frontend

Next.js (App Router) + TypeScript + Tailwind v4, built as a static export served by the FastAPI backend.

```bash
npm install
npm run build   # static export to out/
npm test        # Vitest + React Testing Library
npm run lint
```

All API calls are same-origin (`/api/*`). To try it locally, build, then run the backend with
`STATIC_DIR=<abs path to frontend/out>` and open http://localhost:8000.

Charts use `lightweight-charts`; the heatmap is a small squarified treemap in `src/lib/treemap.ts`.
