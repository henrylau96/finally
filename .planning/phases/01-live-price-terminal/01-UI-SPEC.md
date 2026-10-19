---
phase: 1
slug: live-price-terminal
status: approved
reviewed_at: 2026-10-19
shadcn_initialized: false
preset: none
created: 2026-10-19
---

# Phase 1 - UI Design Contract

> Visual and interaction contract for the Live Price Terminal. Covers the whole terminal grid shell (so later phases inherit tokens) with detail concentrated on the header connection dot and the watchlist. Sources: 01-CONTEXT.md (locked stack and stream contract), planning/PLAN.md sections 2 and 10, test/e2e specs. Open items were decided autonomously and are tagged (decision).

---

## Design System

| Property | Value |
|----------|-------|
| Tool | none (shadcn gate: N, no `components.json`; hand-built Tailwind 4.3 components, in line with the dense terminal aesthetic; registry gate not applicable) |
| Preset | not applicable |
| Component library | none (plain React 19.3 components + Tailwind theme tokens in CSS via `@theme`) |
| Icon library | none in Phase 1 (inline SVG only: sparkline, chevron). Later phases may add `lucide-react` (decision) |
| Font | UI: system sans stack (`ui-sans-serif, system-ui, "Segoe UI", sans-serif`). Numerics and tickers: `ui-monospace, "SF Mono", Menlo, Consolas, monospace` with `font-variant-numeric: tabular-nums`. No webfont download (static export, offline-friendly) (decision) |

---

## Spacing Scale

Declared values (multiples of 4):

| Token | Value | Usage |
|-------|-------|-------|
| xs | 4px | Icon gaps, dot-to-label gap, cell vertical padding |
| sm | 8px | Cell horizontal padding, panel header padding, gap between grid panels |
| md | 16px | Panel body padding where not data-dense, placeholder content padding |
| lg | 24px | Reserved (empty-state vertical rhythm) |
| xl | 32px | Row height of watchlist rows is 32px; reserved for layout gaps |
| 2xl | 48px | Header height |
| 3xl | 64px | Reserved (not used in Phase 1) |

Exceptions:
- Connection dot is 8px diameter (on-scale); its halo ring is 4px.
- Sparkline box is 64px wide x 20px high (multiples of 4).
- Chat dock width 360px expanded, 48px collapsed rail (multiples of 4).
- Watchlist rows are 32px high (dense; no 44px touch target, desktop-first per PLAN.md).

---

## Typography

Exactly 4 sizes, 2 weights (400 regular, 600 semibold).

| Role | Size | Weight | Line Height |
|------|------|--------|-------------|
| Body (cell text, prices, placeholders) | 14px | 400 | 1.5 |
| Label (column headers, panel titles, status text, tickers use 14px/600 as Body-strong) | 12px | 600 | 1.5 |
| Heading (panel/brand title "FinAlly") | 16px | 600 | 1.2 |
| Display (header portfolio total, later phases) | 20px | 600 | 1.2 |

Rules:
- Column headers and panel titles: 12px, 600, uppercase, letter-spacing 0.05em, color `text-muted`.
- Tickers: 14px, 600, monospace. Prices and change %: 14px, 400, monospace, tabular-nums, right-aligned.
- Sparkline has no text.

---

## Color

Theme tokens defined once in CSS (`@theme`) and reused by all phases.

| Role | Value | Usage |
|------|-------|-------|
| Dominant (60%) | `#0d1117` (`--color-bg`) | Page background, watchlist/table body, main chart area |
| Secondary (30%) | `#161b22` (`--color-surface`) panels/header/dock; `#1a1a2e` not used as surface; border `#30363d` (`--color-border`); row hover `#1c2230` | Panels, header bar, chat dock, column header strip |
| Accent (10%) | `#ecad0a` (`--color-accent`) | See reserved list below |
| Text | primary `#e6edf3`, muted `#8b949e` | Body / labels |
| Up (market) | `#3fb950` (`--color-up`) | Positive change text, uptick flash, sparkline when day change >= 0, connected dot |
| Down (market) | `#f85149` (`--color-down`) | Negative change text, downtick flash, sparkline when day change < 0, disconnected dot |
| Warning | `#d29922` (`--color-warn`) | Reconnecting dot only |
| Blue primary | `#209dd7` (`--color-primary`) | Selected-row left border (2px) and focus ring; later: links, main chart line |
| Purple secondary | `#753991` (`--color-submit`) | Reserved for submit buttons in later phases (trade, chat send); not rendered in Phase 1 |
| Destructive | `#f85149` (same as Down) | Not used in Phase 1; later: remove-ticker hover |

Accent reserved for: (1) the "FinAlly" brand wordmark in the header, (2) the active/selected panel title underline. Nothing else in Phase 1. Not used for prices, buttons or hover.

Flash colors: uptick `rgba(63,185,80,0.30)` background, downtick `rgba(248,81,73,0.30)` background, fading to `transparent`.

No pure black or pure white anywhere.

---

## Layout (terminal grid shell)

Desktop-first, full viewport (`h-screen`, no page scroll; panels scroll internally). Gap 8px between panels, 8px outer padding.

```
+--------------------------------------------------------------+
| Header 48px: FinAlly | Total value | Cash |       [dot] label |
+----------------------+-------------------------------+-------+
| Watchlist (live)     | Main chart (placeholder)      | Chat  |
| min 320px, ~28%      | flex 1                        | dock  |
|                      +-------------------------------+ 360px |
|                      | Portfolio / Positions / P&L   |       |
|                      | (placeholders, 3 sub-panels)  |       |
+----------------------+-------------------------------+-------+
```

- CSS grid: columns `minmax(320px, 28%) 1fr auto`; chat dock is the `auto` column (360px, collapsible to 48px rail). Center column rows: main chart `1.4fr`, bottom row `1fr` split into heatmap, positions, P&L placeholders.
- Tablet (<1024px): chat dock starts collapsed; center column stacks under watchlist is NOT required in Phase 1 (UI-13 is Phase 6); layout must not break (no horizontal page scroll).
- Placeholder panels (main chart, heatmap, positions, P&L, chat dock) render a panel title (Label style) and centered muted Body text "Coming soon" using the copy table below. They carry stable test ids: `main-chart` (with `data-ticker` attribute, empty in Phase 1), `heatmap`, `pnl-chart`, `chat-panel`.
- Header placeholders: `total-value` and `cash-balance` elements exist (Display/Body style) showing `--` until Phase 3 populates them (decision: no fake $10,000 in Phase 1, so no misleading data).

---

## Header and Connection Dot (detailed)

- Position: right end of header. Element: `<div data-testid="connection-status" data-status="connected|reconnecting|disconnected" role="status" aria-live="polite">` containing an 8px dot and a 12px Label text.
- States (set from native EventSource: `onopen` -> connected; `onerror` while `readyState === CONNECTING` -> reconnecting; `readyState === CLOSED` -> disconnected). Initial state before first open: `reconnecting` with label "Connecting" (decision; matches 06-sse-reconnect spec expecting `reconnecting` when stream is blocked).

| data-status | Dot | Label text | Motion |
|-------------|-----|-----------|--------|
| connected | `--color-up` solid | Live | none |
| reconnecting | `--color-warn` | Reconnecting | 1s ease-in-out opacity pulse (1 -> 0.4 -> 1), disabled under `prefers-reduced-motion` |
| disconnected | `--color-down` solid | Offline | none |

- Label is muted text color; dot carries the status color. Color is never the only signal: the label text always shows.
- Tooltip (`title`): "Price stream: connected / reconnecting / disconnected".

---

## Watchlist (detailed)

Panel `Watchlist`, title in Label style. Table-like grid of 10 rows in the fixed default order (AAPL, GOOGL, MSFT, AMZN, TSLA, NVDA, META, JPM, V, NFLX); order does not change on price moves (no re-sorting).

Columns (header strip 24px high, Label style, muted):

| Column | Width | Align | Content |
|--------|-------|-------|---------|
| Symbol | 72px | left | ticker, 14px/600 monospace |
| Price | flex, min 88px | right | `price-{TICKER}`, `$` + 2 decimals + thousands separator, e.g. `$190.42` |
| Day % | 72px | right | `+1.23%` / `-0.87%` / `0.00%`, up/down color, always signed, 2 decimals |
| Chart | 64px + 8px gap | center | sparkline SVG |

Row: 32px high, `data-testid="watchlist-row-{TICKER}"`, 1px bottom border `--color-border`, hover bg `#1c2230`, `cursor: pointer`, keyboard focusable (`tabindex=0`, Enter selects), focus ring 2px `--color-primary`. Click/selection behavior is wired in Phase 2 (UI-06); Phase 1 only stores selected ticker and shows 2px `--color-primary` left border + `#1c2230` background on the selected row. Default selected ticker: first row (AAPL) (decision). Remove (x) and add input are Phase 2; reserve ids `watchlist-remove-{TICKER}`, `watchlist-add-input`, `watchlist-add-button`, no UI in Phase 1.

Price cell (`price-{TICKER}`):
- Text content is only the formatted price (E2E `readNumber` strips non-numeric characters and compares text changes). No arrows or extra text inside this element.
- Before the first SSE message: shows `--` and the sparkline area is empty; row is still rendered (rows are static, prices fill in).

Price flash (UI-04):
- Mechanism: on each SSE message, if `direction` is `up` or `down` for the ticker, set `data-flash="up|down"` on the price cell. CSS: `[data-flash="up"] { background-color: rgba(63,185,80,0.30); }` applied immediately (`transition: none`), then removed on the next animation frame pair (double `requestAnimationFrame`) so the base rule `transition: background-color 500ms ease-out` fades it to transparent. Flash covers the price cell only, not the whole row.
- `direction: flat` produces no flash. Rapid consecutive updates restart the flash (remove then re-add attribute).
- Under `prefers-reduced-motion: reduce`, replace the fade with a 150ms fade (flash color stays for color-blind-safe signal).
- Price text color stays primary text (not green/red); only background flashes. Colorblind redundancy: Day % has explicit sign.

Day % (`day-change-{TICKER}` id reserved, not required by E2E): value comes from the backend `day_change_pct`; client does not recompute. Color: `>0` up, `<0` down, `0` muted.

Sparkline (UI-03):
- Inline SVG `<svg width="64" height="20" viewBox="0 0 64 20">` with one `<polyline fill="none" stroke-width="1.5" stroke-linejoin="round" vector-effect="non-scaling-stroke">`. No axes, no fill, no tooltip, `aria-hidden="true"`.
- Data: client ring buffer of last 120 prices per ticker from SSE since page load; appends one point per SSE message (~500ms, so ~60s of history at full buffer).
- Scale: per-render min/max of the buffer mapped to 2px..18px vertical padding; flat series (max==min) draws a centered horizontal line. X spreads buffered points across full 64px width (so it fills left to right visually as data arrives; with <2 points render nothing).
- Stroke color (decision): follows the sign of `day_change_pct` (`--color-up` if >= 0, else `--color-down`), consistent with the Day % text next to it.
- Does not animate; updates replace `points` attribute.

Empty / error states in watchlist:
- No data yet (stream connecting): price and Day % cells show `--` muted; sparkline blank.
- Stream offline: last known prices stay visible; price and Day % text switch to `--color-text-muted` while `data-status != connected` (decision; keeps 4.5:1 contrast, unlike opacity dimming) so stale data is not read as live; flashes stop.

---

## Interaction Contract

| Interaction | Behavior |
|-------------|----------|
| Page load | Header + grid render immediately (static); EventSource opens `/api/stream/prices`; dot "Connecting" (reconnecting state) until `onopen` |
| SSE message | Parse JSON map; update price, Day %, sparkline buffer, flash for all tickers in one React state update (one render per message) |
| Row hover / focus | Background `#1c2230`, 100ms transition |
| Row click / Enter | Sets selected ticker (visual only in Phase 1) |
| Chat dock toggle | Chevron button in dock header collapses to 48px rail; state is in-memory only. `aria-expanded` set. Placeholder in Phase 1 |
| Keyboard | Tab order: header (none interactive), watchlist rows, chat toggle. Visible focus ring everywhere |
| Accessibility | `lang="en"`, `role="status"` on connection indicator, rows use `role="row"` within `role="table"` grid semantics, text contrast >= 4.5:1 on `#0d1117` (primary `#e6edf3`, muted `#8b949e` ~ 6:1) |

---

## Copywriting Contract

| Element | Copy |
|---------|------|
| Primary CTA | none in Phase 1 (no actions yet). Reserved for Phase 3: "Buy" / "Sell" |
| Brand / title | "FinAlly" (header), page `<title>`: "FinAlly - AI Trading Workstation" |
| Connection labels | "Live", "Reconnecting", "Offline", initial "Connecting" |
| Empty state heading (watchlist before first tick) | "Waiting for prices" |
| Empty state body | "Prices appear as soon as the stream connects. No action needed." |
| Error state (stream offline) | reconnecting: "Reconnecting to price stream. Prices shown may be stale."; disconnected (EventSource CLOSED, no auto-retry): "Price stream closed. Reload the page to retry." (shown as a 12px muted line at the top of the watchlist panel only when status is not connected) |
| Placeholder panels | Main chart: "Select a ticker to see its chart. Coming soon." Heatmap: "Portfolio heatmap. Coming soon." Positions: "Positions. Coming soon." P&L: "P&L chart. Coming soon." Chat dock: "AI assistant. Coming soon." |
| Header placeholders | Labels "Total value" and "Cash"; values `--` |
| Destructive confirmation | none: no destructive actions in this phase |

---

## Registry Safety

| Registry | Blocks Used | Safety Gate |
|----------|-------------|-------------|
| shadcn official | none (shadcn not initialized, Tool: none) | not applicable |
| third-party | none | not applicable |

---

## Test Hooks (E2E contract exposed in Phase 1)

| test id | Element | Notes |
|---------|---------|-------|
| `connection-status` | header indicator | `data-status` = connected / reconnecting / disconnected |
| `watchlist-row-{TICKER}` | each of 10 rows | visible on first render, before any price arrives |
| `price-{TICKER}` | price cell | text parses to a number once streaming, changes over time |
| `total-value`, `cash-balance` | header values | present, `--` until Phase 3 |
| `main-chart`, `heatmap`, `pnl-chart`, `chat-panel` | placeholder panels | present; `main-chart` has `data-ticker` |

---

## Checker Sign-Off

- [ ] Dimension 1 Copywriting: PASS
- [ ] Dimension 2 Visuals: PASS
- [ ] Dimension 3 Color: PASS
- [ ] Dimension 4 Typography: PASS
- [ ] Dimension 5 Spacing: PASS
- [ ] Dimension 6 Registry Safety: PASS

**Approval:** pending
