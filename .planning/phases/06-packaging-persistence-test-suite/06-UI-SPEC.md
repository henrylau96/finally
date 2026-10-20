---
phase: 6
slug: packaging-persistence-test-suite
status: approved
reviewed_at: 2026-10-20
shadcn_initialized: false
preset: none
created: 2026-10-20
---

# Phase 6 - UI Design Contract

> Extends the approved Phase 1-4 contracts. All tokens, spacing, typography, color and component rules are inherited unchanged; this document only adds responsive behaviour (UI-13) and the data-testid contract (UI-14). Sources: PLAN.md sections 2, 10, 12; current `frontend/src/components/*`; `test/e2e/*.spec.ts`. Autonomous choices are tagged (decision). No questions were asked (PLAN.md is the spec).

Focal point (inherited): the main chart and the header total value; responsive changes must keep both visible at every supported width.

---

## Design System

| Property | Value |
|----------|-------|
| Tool | none (no `components.json`; shadcn gate: N per Phase 1, registry gate not applicable) |
| Preset | not applicable |
| Component library | none (React + Tailwind `@theme` tokens in `globals.css`) |
| Icon library | none (no new icons) |
| Font | Inherited: system sans; monospace + tabular-nums for tickers and prices |

---

## Spacing Scale

Inherited scale (4, 8, 16, 24, 32, 48, 64). Phase 6 usage:

| Token | Value | Phase 6 usage |
|-------|-------|---------------|
| sm | 8px | Grid gap and page padding at every breakpoint (unchanged) |
| xl | 32px | Minimum tap-friendly control height stays 32px (no growth at tablet) |
| 2xl | 48px | Collapsed chat dock width (unchanged `w-12`) |

Exceptions: expanded dock overlay width stays the inherited 360px; watchlist column minimum 240px at tablet (was 320px); stacked-panel minimum height 240px (60 x 4, tablet only). Breakpoint values (768, 1024, 1280px) are viewport thresholds, not spacing tokens.

---

## Typography

Inherited: exactly 4 sizes (12 / 14 / 16 / 20), 2 weights (400, 600), body line height 1.5. Phase 6 adds no sizes or weights and does not shrink type at tablet width.

| Role | Size | Weight | Line Height |
|------|------|--------|-------------|
| Body | 14px | 400 | 1.5 |
| Label | 12px | 600 | 1.5 |
| Heading | 16px | 600 | 1.2 |
| Display | 20px | 600 | 1.2 |

---

## Color

Inherited, no change: 60% `--color-bg` (`#0d1117`), 30% `--color-surface` + `--color-border`, 10% accent.

| Role | Value | Usage |
|------|-------|-------|
| Dominant (60%) | `--color-bg` `#0d1117` | Page background |
| Secondary (30%) | `--color-surface` | Panels, chat dock |
| Accent (10%) | `#ecad0a` | Unchanged |
| Destructive | `--color-down` | Unchanged |

Accent reserved for (unchanged): (1) "FinAlly" wordmark, (2) active panel title underline. The overlay dock at tablet width gets a 1px `--color-border` edge and no shadow or new color (decision, flat terminal look).

---

## Responsive Layout (UI-13)

Desktop-first, functional at tablet. Target viewports: 1440x900 (primary), 1280x800, 1024x768, 768x1024. Phone widths are out of scope.

| Viewport width | Layout |
|----------------|--------|
| >= 1280px (wide) | Inherited Phase 1-4 layout unchanged: columns `minmax(320px,28%) / 1fr / dock`; dock expanded 360px by default; center column rows chart / trade bar / bottom row of Heatmap + Positions + P&L in 3 columns; page does not scroll |
| 1024-1279px | Same 3 columns but watchlist `minmax(240px,26%)`; dock defaults to collapsed (48px); bottom row stays 3 columns with `minmax(0,...)` so nothing overflows; page does not scroll |
| 768-1023px (tablet) | Same columns as 1024-1279 (watchlist `minmax(240px,30%)`, dock collapsed); bottom row becomes 2 columns: Positions spans the full first row, Heatmap and P&L share the second row; the page may scroll vertically (`overflow-y-auto` on the page wrapper, panels get `min-h-[240px]`, main chart `min-h-[240px]`) |
| < 768px | Not supported; layout simply keeps the 768 rules (horizontal scroll is acceptable here only) |

Rules (decision):

1. No horizontal page scroll from 768px up. Every grid child uses `min-w-0`; tables scroll inside their own panel (`overflow-auto`), never the page.
2. Chat dock below 1280px starts collapsed (initial state from `matchMedia("(min-width: 1280px)")` on mount; no resize listener, no persistence). When the user expands it below 1280px it renders as an overlay: `absolute inset-y-0 right-0 w-[360px] z-10`, `--color-surface`, 1px `--color-border`, over the center column; the grid keeps a 48px dock slot so the other panels do not reflow. Collapse returns to the 48px strip. At >= 1280px expand/collapse reflows as before (inherited).
3. `chat-panel` stays in the DOM and visible in every state (Phase 4 contract, `data-collapsed` kept). Content stays mounted when collapsed.
4. Header keeps one row at 768px: wordmark, total value, cash, connection dot. The "as of" / stale badge text may hide below 1024px (`hidden lg:inline`) but the `stale-badge` element still renders when stale (E2E asserts `toHaveCount(0)` only when fresh).
5. Trade bar keeps one row; the error text truncates (inherited) at narrow widths.
6. Sparklines, price flash, treemap and charts keep using `useSize`/ResizeObserver, so resizing needs no extra code.
7. Touch/pointer: all clickable rows and buttons are already >= 32px high; no hover-only interaction is required to complete a flow (watchlist remove button is visible on focus and on row hover; below 1024px it is always visible, decision).

---

## Copywriting Contract

No new user-facing copy in this phase. All copy is inherited from Phases 1-4.

| Element | Copy |
|---------|------|
| Primary CTA | Inherited: "Buy" / "Sell" (trade bar), "Send" (chat) |
| Empty state heading | Inherited (watchlist, positions, heatmap, P&L, chat empty states unchanged) |
| Empty state body | Inherited |
| Error state | Inherited ("Could not reach FinAlly. Try again.", trade and watchlist errors unchanged) |
| Destructive confirmation | None, by design (PLAN.md: no confirmation dialogs; watchlist remove and trades are immediate) |

---

## Test Hooks (UI-14)

Rule: hooks are `data-testid` attributes only; tests never select by CSS class or text where a hook exists. Dynamic hooks use the uppercase ticker. State is exposed through `data-*` attributes, not CSS classes.

### Already present in the code (keep unchanged)

| test id | Element | State attributes |
|---------|---------|------------------|
| `total-value`, `cash-balance`, `stale-badge` | Header values / stale marker | text is formatted `$` amount |
| `connection-status` | Header dot + label | `data-status` = connected / reconnecting / disconnected |
| `watchlist-row-{T}`, `price-{T}`, `day-change-{T}`, `watchlist-remove-{T}` | Watchlist row, price cell, day change, remove button | price cell: `data-flash` = up / down briefly |
| `watchlist-add-input`, `watchlist-add-button`, `watchlist-add-error`, `watchlist-empty` | Add form, error, empty | |
| `main-chart`, `main-chart-ticker`, `main-chart-price`, `main-chart-empty` | Main chart | `main-chart` has `data-ticker` |
| `trade-bar`, `trade-ticker`, `trade-quantity`, `buy-button`, `sell-button`, `trade-error` | Trade bar | `trade-error` has `role="alert"` |
| `positions`, `position-row-{T}`, `positions-empty` | Positions table | |
| `heatmap`, `heatmap-cell-{T}`, `heatmap-empty` | Treemap | cell: `data-pnl`, `data-selected` |
| `pnl-chart`, `pnl-empty` | P&L chart | `pnl-chart` has `data-points` |
| `chat-panel`, `chat-messages`, `chat-message`, `chat-action`, `chat-loading`, `chat-input`, `chat-send`, `chat-form`, `chat-empty`, `chat-example` | Chat dock | per Phase 4 table |

### Missing, to add in Phase 6

| test id | Element | Needed by (PLAN.md section 12 scenario) |
|---------|---------|------------------------------------------|
| `watchlist` | Watchlist panel root (via `Panel testId`) | Fresh start: panel visible; tablet layout assertions |
| `sparkline-{T}` | Sparkline `<svg>`/canvas wrapper in each watchlist row; `data-points` = number of accumulated points | Fresh start: sparklines fill progressively |
| `chat-toggle` | Dock collapse/expand button (keeps `aria-expanded`; `aria-label` "Expand chat" / "Collapse chat" if icon-only) | Responsive tests: expand/collapse the dock |
| `app-header` | Header root `<header>` | Layout smoke: header present at all viewports |
| `position-qty-{T}` | Quantity cell inside the position row | Buy/sell: assert quantity after trade without parsing the whole row |
| `position-pnl-{T}` | Unrealized P&L cell; `data-pnl` = up / down / flat | Buy/sell: P&L sign |

Everything else needed by the six scenarios (fresh start, watchlist add/remove, buy, sell, heatmap + P&L data, mocked chat trade, SSE status/reconnect) is already covered by existing hooks. Existing specs `01` to `06` in `test/e2e/` must pass unchanged; the new hooks are additive and no existing id is renamed.

### Scenario to hook map

| Scenario | Hooks |
|----------|-------|
| Fresh start | `watchlist-row-{T}` x10, `cash-balance`, `total-value`, `price-AAPL`, `sparkline-AAPL`, `connection-status[data-status=connected]` |
| Add / remove ticker | `watchlist-add-input`, `watchlist-add-button`, `watchlist-row-{T}`, `watchlist-remove-{T}`, `watchlist-add-error` |
| Buy / sell | `trade-ticker`, `trade-quantity`, `buy-button`, `sell-button`, `trade-error`, `cash-balance`, `position-row-{T}`, `position-qty-{T}` |
| Heatmap / P&L | `heatmap`, `heatmap-cell-{T}[data-pnl]`, `pnl-chart[data-points]` |
| Mocked AI chat | `chat-input`, `chat-send`, `chat-loading`, `chat-message[data-role]`, `chat-action[data-ok]` |
| SSE resilience | `connection-status[data-status]`, `price-{T}` |
| Responsive smoke (new, optional) | `app-header`, `watchlist`, `chat-toggle`, `chat-panel[data-collapsed]`; assert `document.documentElement.scrollWidth <= innerWidth` at 1280, 1024 and 768 wide |

---

## Registry Safety

| Registry | Blocks Used | Safety Gate |
|----------|-------------|-------------|
| shadcn official | none (Tool: none) | not applicable |
| third-party | none | not applicable |

No new npm dependency.

---

## Decisions Log (autonomous)

1. Three breakpoints: 1280 (full), 1024 (dock collapses by default), 768 (bottom row restacks, page may scroll vertically). Phones unsupported.
2. Tablet dock expands as an overlay over the center column so panels never squeeze below usable width; initial state chosen once via `matchMedia`, no persistence.
3. No horizontal page scroll at 768px and up; tables scroll inside panels.
4. No visual redesign: colors, type, spacing tokens and copy are inherited.
5. Test hooks are additive: 6 new ids; no renames, so existing specs stay valid.
6. Hook state is exposed via `data-*` attributes (`data-status`, `data-flash`, `data-pnl`, `data-ok`, `data-collapsed`, `data-points`), never via class names.

---

## Checker Sign-Off

- [x] Dimension 1 Copywriting: PASS
- [x] Dimension 2 Visuals: PASS (FLAG: chat-toggle label, focal point - addressed)
- [x] Dimension 3 Color: PASS
- [x] Dimension 4 Typography: PASS
- [x] Dimension 5 Spacing: PASS
- [x] Dimension 6 Registry Safety: PASS

**Approval:** approved 2026-10-20
