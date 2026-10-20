---
phase: 3
slug: trading-portfolio
status: approved
reviewed_at: 2026-10-19
shadcn_initialized: false
preset: none
created: 2026-10-19
---

# Phase 3 - UI Design Contract

> Extends the approved Phase 1 and Phase 2 contracts (`01-UI-SPEC.md`, `02-UI-SPEC.md`). All tokens, spacing, typography, color rules and the Phase 2 "Checker Clarifications" are inherited unchanged; this document only adds or overrides. Sources: 03-CONTEXT.md (locked), 02-UI-REVIEW.md (findings folded in), test/e2e/01, 03, 04 and helpers.ts. Autonomous choices are tagged (decision).

---

## Design System

| Property | Value |
|----------|-------|
| Tool | none (no `components.json`; shadcn gate: N per Phase 1, registry gate not applicable) |
| Preset | not applicable |
| Component library | none (React 19.3 + Tailwind 4.3 `@theme` tokens in `globals.css`) |
| Icon library | none (text glyphs only) |
| Chart library | Lightweight Charts 5.2 (P&L line, canvas); treemap is hand-built divs (no new dependency); sparklines stay inline SVG |
| Font | Inherited: system sans for UI; monospace + tabular-nums for tickers, prices, money, quantities, percentages |

---

## Spacing Scale

Inherited scale (4, 8, 16, 24, 32, 48, 64). Phase 3 usage:

| Token | Value | Phase 3 usage |
|-------|-------|---------------|
| xs | 4px | Gap between trade fields and buttons; heatmap cell gap is 2px (exception) |
| sm | 8px | Trade bar padding; table cell horizontal padding; heatmap cell inner padding; empty-state padding |
| md | 16px | Header gap between value groups (inherited gap-6 = 24px stays) |
| lg | 24px | Trade error slot height; positions column header strip |
| xl | 32px | Trade bar control height; positions row height |
| 2xl | 48px | Header height (unchanged) |

Exceptions:
- Trade bar controls are 32px high (matches add form and row density; desktop-first).
- Heatmap cells are separated by a 2px gap (rendered as 1px inset on each cell via `border: 1px solid var(--color-bg)`), so adjacent rectangles read as distinct without a layout gap token (decision).
- Trade ticker input 80px wide, quantity input 96px wide, Buy and Sell buttons 56px wide (fit "Sell" at 14/600 with 16px side padding).
- Positions grid uses fixed numeric columns of 72px / 80px (see below) to fit `$12,345.67` at 14px tabular-nums.

---

## Typography

Inherited: exactly 4 sizes (12 / 14 / 16 / 20), 2 weights (400, 600). No new sizes or weights.

| Phase 3 element | Size | Weight | Notes |
|-----------------|------|--------|-------|
| Header total value | 20px | 600 | mono tabular-nums (inherited, already `text-xl font-semibold`) |
| Header cash | 14px | 400 | mono tabular-nums (inherited) |
| Trade input text and placeholder | 14px | 400 | mono; ticker input uppercase |
| Buy / Sell labels | 14px | 600 | |
| Trade error text | 12px | 400 | |
| Positions column headers | 12px | 600 | uppercase, tracking 0.05em, muted (same as watchlist header) |
| Positions ticker | 14px | 600 | mono |
| Positions numerics | 14px | 400 | mono tabular-nums |
| Heatmap cell ticker | 14px | 600 | mono |
| Heatmap cell P&L % | 12px | 400 | mono tabular-nums |
| Empty-state text | 14px | 400 | muted |
| P&L chart axis / crosshair | 12px | 400 | mono (same options as main chart) |

Line height: body 1.5, headings 1.2 (inherited).

---

## Color

Inherited split: 60% `--color-bg` `#0d1117`, 30% `--color-surface` `#161b22` + border `#30363d`, 10% accent `#ecad0a`. No new tokens. The heatmap scale is derived from `--color-up` `#3fb950` and `--color-down` `#f85149` using alpha.

### Phase 3 color assignments

| Element | Color |
|---------|-------|
| Trade bar strip | background `--color-surface`, 1px `--color-border` top and bottom |
| Trade inputs | background `--color-bg`, 1px `--color-border`, text `--color-text`, placeholder `--color-text-muted` |
| Buy button (solid) | background `--color-submit` `#753991`, text `--color-text`, hover `filter: brightness(1.1)`, disabled opacity 0.5 |
| Sell button (outline) | transparent background, 1px `--color-submit` border, text `--color-text`; hover background `rgba(117,57,145,0.2)`; disabled opacity 0.5 (decision: derived from submit token with alpha, no new hue) |
| Trade error | `--color-down`, 12px |
| P&L positive text (positions table, header deltas) | `--color-up`; negative `--color-down`; zero `--color-text-muted` |
| Heatmap cell fill | see "Heatmap color scale" |
| Heatmap cell text | `--color-text` (tickers) and `--color-text` at full opacity for P&L % (contrast is held by the alpha cap) |
| P&L chart line | `--color-primary` `#209dd7` (blue, matches main chart; line color does not change with sign, decision) |
| P&L chart fill | none (LineSeries) |
| P&L chart baseline marker | dashed price line at the starting value `10000`, `--color-text-muted` (decision: shows profit vs loss against the seed cash) |
| Chart grid/crosshair/axis | identical to the main chart options block in the Phase 2 spec |
| Header total value | `--color-text`; muted `--color-text-muted` when status is not `connected` (stale rule, inherited from chart header) |
| Active panel underline | `--color-accent` 2px bottom border on the panel title strip |

Accent `#ecad0a` reserved for (unchanged): (1) "FinAlly" wordmark, (2) active panel title underline. In Phase 3 the active panels are Watchlist and Main chart (review fix 1). Nothing else uses accent: not trade buttons, not P&L, not heatmap.

Destructive color `--color-down`: remove-ticker hover (inherited), trade error text, negative P&L. Selling is not styled as destructive (decision: Sell uses purple outline per CONTEXT).

---

## Layout

Phase 1 outer grid is unchanged (`minmax(320px,28%) 1fr auto`; narrow-width behavior stays in Phase 6, UI-13). The center column changes from two rows to three:

```
+----------------------------------------------------------+
| MAIN CHART (title strip, accent underline)               |
| ...chart header 40px + chart (1.4fr)                     |
+----------------------------------------------------------+
| Trade bar (auto, 40px strip + 24px error slot = 64px)    |
+----------------------------------------------------------+
| HEATMAP (1fr)   | POSITIONS (1.6fr)    | P&L (1fr)       |   bottom row (1fr)
+----------------------------------------------------------+
```

- Center column: `grid-rows-[1.4fr_auto_1fr]`, gap 8px, `min-h-0 min-w-0`. The trade bar sits directly below the main chart panel and is its own bordered block (not inside the chart panel).
- Bottom row: `grid-cols-[minmax(0,1fr)_minmax(0,1.6fr)_minmax(0,1fr)]`, gap 8px. Positions gets the extra width because it has six columns (decision). Each is a `Panel`; Positions body scrolls internally (`overflow-auto`), Heatmap and P&L bodies are `overflow-hidden`.
- Panel title strip stays "Heatmap", "Positions", "P&L" (uppercase via existing style). Review fix 1: `Panel` gets an optional `active` prop that swaps the title `border-b` for `border-b-2 border-accent`; Watchlist and Main chart pass `active`. Heatmap, Positions, P&L do not.
- Review nit folded: placeholder paragraphs are gone for these three panels; any remaining centered text (empty states) is vertically and horizontally centered with `flex h-full items-center justify-center`.

---

## Header (UI-02, PORT-05)

| Property | Contract |
|----------|----------|
| Total value | `data-testid="total-value"`, formatted with `formatPrice` (`$10,000.00`), 20px/600 mono tabular-nums. Initial render before data: `--`. Value = cash + sum(quantity x live SSE price, fallback avg cost), recomputed on each tick |
| Cash | `data-testid="cash-balance"`, `formatPrice`, 14px mono tabular-nums. From `GET /api/portfolio` on load and after each trade; `--` until the first response |
| Parsing | Text contains only `$`, digits, `,` and `.` (and a leading `-` only if ever negative); no extra characters inside the test-id elements (E2E numeric parser strips non-numeric) |
| Update | No flash on header values (the watchlist cell owns flash). Values simply re-render; layout width is stable because both use tabular-nums |
| Stale | When status is not `connected`, total value switches to `--color-text-muted` |
| Labels | Existing "Total value" and "Cash" labels (12px/600 uppercase muted) unchanged |

---

## Trade Bar (PORT-01..04, UI-07)

Container: `data-testid="trade-bar"`, a `<form>` below the main chart. Strip is `--color-surface`, 8px padding, 32px controls, 4px gaps; below it a fixed 24px error slot inside the same block, always rendered.

```
[ ticker 80px ][ quantity 96px ][ Buy 56px ][ Sell 56px ]            (flex, left aligned)
[ trade-error slot, 24px, 12px text, 8px horizontal padding ]
```

| Property | Contract |
|----------|----------|
| Ticker input | `data-testid="trade-ticker"`, `type="text"`, `placeholder="Ticker"`, `aria-label="Trade ticker"`, `maxLength=5`, `autocomplete="off"`, `spellcheck=false`, value uppercased on change, CSS uppercase. Prefilled with the selected ticker and follows selection changes (selecting a watchlist or position row replaces the value). Manual edits persist until the next selection change |
| Quantity input | `data-testid="trade-quantity"`, `type="text"`, `inputMode="decimal"`, `placeholder="Quantity"`, `aria-label="Trade quantity"`, `autocomplete="off"`. Text, not `type=number`, so Playwright `fill("2.5")` and the 4-decimal rule are controlled by our validation (decision) |
| Buy button | `data-testid="buy-button"`, `type="submit"` is NOT used; both buttons are `type="button"` and call `submit(side)`. Enter in either input submits Buy (decision: primary action). Label "Buy", `aria-label="Buy shares"` |
| Sell button | `data-testid="sell-button"`, `type="button"`, label "Sell", `aria-label="Sell shares"`, outline style |
| Client validation | Ticker trimmed + uppercased must match `^[A-Z]{1,5}$`; quantity must parse as a finite number > 0 with at most 4 decimals. Fails: no request, error copy below |
| Pending | While the POST is in flight: both buttons and both inputs `disabled`, `aria-busy="true"` on the form, cursor `progress`. Labels do not change. Prevents double submit |
| Success | Quantity cleared; ticker kept; error cleared; header cash, positions, heatmap and P&L refetch/refresh; focus returns to the quantity input. No toast, no confirmation dialog (per PLAN.md) |
| Failure | Error shown in the fixed slot (`data-testid="trade-error"`, `role="alert"`); inputs keep their values; focus returns to the quantity input (consistent with the review fix 2 pattern) |
| Error clearing | On next keystroke in either input or on next submit. The `trade-error` element is only present in the DOM while an error exists; the slot wrapper itself (24px) is always rendered (decision, no layout shift; E2E asserts `toBeVisible` on the error element) |
| Focus ring | 2px `--color-primary` (inherited `:focus-visible`) |
| Tab order | Ticker, quantity, Buy, Sell |

Input and button radius 0, input border 1px `--color-border` (flat terminal look, inherited).

### Error copy (fixed, short enough for one 12px line in the slot; truncates with ellipsis and full text in `title`)

| Condition | Copy |
|-----------|------|
| Invalid ticker (client or 422) | "Enter a ticker of 1-5 letters." |
| Invalid quantity (client or 422) | "Enter a quantity above 0 (up to 4 decimals)." |
| 400 insufficient cash | Server `detail` verbatim: "Insufficient cash: need $X, have $Y" (decision: show the server message, it is already specific; amounts formatted by the server) |
| 400 oversell | Server `detail` verbatim: "Cannot sell N AAPL; you hold M" |
| 400 other business rule | Server `detail` verbatim |
| Network or 5xx | "Could not place the trade. Try again." |

---

## Positions Table (PORT-06, UI-08)

Panel "Positions". Body is `role="grid"` with `aria-label="Positions"`, rowgroup/row/columnheader/gridcell semantics as in the watchlist (Phase 2 Table Semantics).

| Property | Contract |
|----------|----------|
| Column header strip | 24px, `--color-surface`, 12px/600 uppercase muted, sticky at the top of the scrolling body (review nit folded) |
| Columns | Symbol, Qty, Avg cost, Price, P&L, Chg % |
| Grid template | `64px minmax(56px,1fr) 80px 80px 80px 72px`, 8px column gap, 8px horizontal padding, 2px transparent left border reserved for selection |
| Alignment | Symbol left; all numeric columns right-aligned, mono tabular-nums |
| Rows | `data-testid="position-row-{TICKER}"`, 32px high, 1px bottom border, `role="row"`, `tabindex=0`, `aria-selected` true/false, order = market value descending (decision, matches treemap order) |
| Formatting | Qty: up to 4 decimals, trailing zeros trimmed, thousands separator (`2`, `0.5`, `1,250.25`). Avg cost, Price: `formatPrice` (`$190.42`). P&L: signed dollars `+$12.34` / `-$5.00` / `$0.00`. Chg %: `formatPct` (`+1.23%`, `-0.45%`, `0.00%`) |
| P&L coloring | P&L and Chg % cells colored: positive `--color-up`, negative `--color-down`, zero `--color-text-muted`. Sign is always shown in text, so color is not the only signal |
| Live update | Price, P&L, Chg % recompute on each SSE tick from `quantity`, `avg_cost` and live price (fallback `current_price` from the API, then avg cost). Price cell carries the existing `price-cell` flash behavior (decision: reuse, same class and `data-flash`); P&L cells do not flash |
| Row selection | Click, Enter or Space selects the ticker in the main chart (shared `selected` state) and prefills the trade ticker. Selected: `--color-row-hover` background plus 2px `--color-primary` left border and `aria-selected="true"`; hover: background only. Same states as the watchlist row |
| Empty state | `data-testid="positions-empty"`, centered muted 14px: "No positions yet." second line 12px muted: "Buy shares with the trade bar to see them here." |
| Loading (before first portfolio response) | Body empty, no copy (avoids flashing the empty state; decision) |
| Sold-out | Row disappears when the API returns no position for the ticker; if it was selected the selection stays (chart still shows it) |

---

## Heatmap (PORT-07, UI-09)

Panel "Heatmap", container `data-testid="heatmap"` (on the panel, as in Phase 1). Inside the body, a relatively positioned `div` (`data-testid="heatmap-canvas"` optional) fills the body; cells are absolutely positioned divs with percent geometry.

### Layout algorithm

- Squarified treemap, hand-built (`frontend/src/lib/treemap.ts`, pure function: `squarify(items: {id, value}[], width, height) -> {id, x, y, w, h}[]`). Items sorted by value descending, value = market value (quantity x live price, fallback avg cost). Zero or negative values are excluded.
- Recomputed when positions change or when a tick changes a value by any amount; rects are computed in 0..100 percent space (unit square scaled by the container aspect via `ResizeObserver`) so resize does not need re-fetch. No animation on layout change (decision, avoids flicker on every 500ms tick); cell fill changes use `transition: background-color 300ms ease-out`, none under `prefers-reduced-motion`.
- One position fills the whole body.

### Cell

| Property | Contract |
|----------|----------|
| Element | `<div data-testid="heatmap-cell-{TICKER}" data-pnl="positive|negative|flat" role="img" aria-label="{TICKER}: {pnl %}, market value {formatPrice}">` |
| `data-pnl` | `positive` when pnl_pct > 0.005, `negative` when pnl_pct < -0.005, otherwise `flat` (based on the displayed rounded value, so `0.00%` is always flat) |
| Border | 1px solid `--color-bg` on all sides (creates the 2px gap between neighbors) |
| Padding | 8px |
| Labels | Ticker (14px/600 mono, `--color-text`) on the first line; P&L % (12px/400 mono tabular-nums, `formatPct`) on the second line. Left aligned, top-left of the cell |
| Click | Clicking a cell selects that ticker (main chart + trade prefill). Cursor pointer, `tabindex=0`, Enter/Space select, hover shows 1px `--color-text-muted` inset outline |
| Min-size label rules | Measured in rendered px: if cell width < 56px or height < 28px: hide both labels (title attribute `{TICKER} {pnl %}` still gives a tooltip). If height < 44px but both fit width-wise: show the ticker only. Otherwise show both. Text never wraps; overflow hidden with ellipsis |

### Color scale (P&L %, derived from tokens with alpha)

| Condition | Fill |
|-----------|------|
| Flat (rounded pct = 0.00%) | `--color-row-hover` `#1c2230` (neutral, no hue) |
| Positive | `rgba(63,185,80, a)` (`--color-up`) |
| Negative | `rgba(248,81,73, a)` (`--color-down`) |

Alpha `a = 0.25 + 0.55 * min(|pnl_pct| / 10, 1)`: 0.25 at the smallest non-flat move, linearly to a cap of 0.80 at a 10% move or more. The cap keeps white-ish `--color-text` readable on both hues (decision). Sign and percentage are always printed in the label, so color is not the only signal (except in hidden-label small cells, which expose it via title and aria-label).

### States

| State | Display |
|-------|---------|
| Empty (no positions) | `data-testid="heatmap-empty"`, centered muted text 14px "No positions yet." with 12px muted second line "Your holdings appear here after your first trade." The `heatmap` container remains in the DOM |
| Loading | Body empty (no copy) until the first portfolio response |
| Normal | Cells as above |

---

## P&L Chart (PORT-08, UI-10)

Panel "P&L", container `data-testid="pnl-chart"` on the panel, with `data-points="{N}"` where N is the number of points currently set on the series (0 when empty). The chart canvas is created inside the panel body whenever the chart is shown, so `pnl-chart canvas` exists for E2E (Lightweight Charts creates its own canvas).

### Chart options

Same options block as the main chart (Phase 2), with these differences:
- Series: `LineSeries` (not area), `color: '#209dd7'`, `lineWidth: 2`, `lastValueVisible: true`, `priceLineVisible: false`, `crosshairMarkerRadius: 4`.
- Baseline: `series.createPriceLine({ price: 10000, color: '#8b949e', lineStyle: LineStyle.Dashed, lineWidth: 1, axisLabelVisible: false, title: '' })` (decision).
- `localization.priceFormatter`: `formatPrice` style (`$10,000.00`), `timeFormatter` HH:mm:ss for intraday; `timeScale.timeVisible: true`, `secondsVisible: false`.
- Colors come from one shared constants module (`frontend/src/lib/chartTheme.ts`) used by both charts, replacing the duplicated hex literals in `MainChart.tsx` (review finding folded: color pillar). Values are the existing token hexes.
- Keep the attribution logo on (license), as in Phase 2.
- `autoSize: true`; chart created once, `setData` on refetch, cleanup resets refs on teardown (Phase 2 pattern).

### Data

- Source: `GET /api/portfolio/history` (last 500 snapshots, oldest first, `{total_value, recorded_at}`), refetched on mount, after each successful trade, and every 30 s.
- Time = UTC seconds of `recorded_at`; points with duplicate seconds collapse to the latest (series requires strictly ascending times).
- Live tail: the last point is not synthesized from SSE; the chart reflects snapshots only (decision, keeps `data-points` equal to history length and avoids a mismatch with the header).
- Refetch failure: keep the previous data, no error UI (decision); a failed first load shows the empty state.

### States

| State | Condition | Display |
|-------|-----------|---------|
| Empty | 0 points | Centered overlay `data-testid="pnl-empty"`: 14px muted "No portfolio history yet." and 12px muted "The chart fills in as snapshots are recorded." `data-points="0"` |
| One point | exactly 1 point | The chart renders a single marker (crosshair-sized dot via `LineSeries` `pointMarkersVisible: true`) with the baseline line; overlay is NOT shown; `data-points="1"`. Axis shows the value. |
| Normal | 2+ points | Line, `pointMarkersVisible: false` |

Startup records a snapshot, so a fresh load normally has at least 1 point and `data-points > 0` quickly (E2E polls this).

---

## Interaction Contract (additions)

| Interaction | Behavior |
|-------------|----------|
| Page load | In addition to Phase 2: fetch `GET /api/portfolio` and `GET /api/portfolio/history`; header, positions, heatmap, P&L fill when they resolve |
| Select ticker (watchlist row, position row, heatmap cell) | One shared `selected` state: main chart swaps, trade ticker is prefilled/replaced, selected styling applies to the matching watchlist and positions rows |
| Buy / Sell | Validate, POST `/api/portfolio/trade`, pending, on success refetch portfolio and history, update header and tables; cash updates from the response `cash_balance` immediately |
| Trade on a ticker not in the watchlist | Allowed (server starts streaming it). No watchlist change; it appears in positions/heatmap with fallback avg cost until its first tick |
| Esc in the quantity input | Clears the quantity and the trade error (decision, mirrors the add form) |
| Stream loss | Header total value muted; positions P&L stays at last values; no extra notice (the watchlist notice carries the message) |
| Tab order | Add input, Add button, watchlist rows and remove buttons, chart (none), trade ticker, quantity, Buy, Sell, positions rows, heatmap cells, chat toggle |

### Folded Phase 2 fixes

1. Active panel title: `Panel` `active` prop adds `border-b-2 border-accent` (Watchlist and Main chart). Title strip height stays 24px (the extra border replaces, not adds to, the 1px border: use `box-sizing` with `border-b-2` and reduce `py` by 1px is NOT allowed, accept 25px, decision; no off-scale CSS).
2. Add input refocus: `WatchlistAddForm` refocuses the input after a failed add (move the focus call before the error return or into `finally`), so keyboard users keep their place. Applies to success and failure.
3. `pl-[10px]` in `Watchlist.tsx` replaced by `pl-2` plus a matching 2px transparent left border on the header row (kept from the review's top-3 fix list as it is off-scale).
4. Chart hex literals consolidated in `chartTheme.ts` (see P&L chart).
5. Selected default `AAPL` while loading: selection starts empty until the watchlist resolves, then falls to AAPL if present, otherwise the first row (decision; fixes the "AAPL shown while loading" finding).

Out of scope (Phase 6): narrow-width center column, dock collapse, tablet layout.

---

## Copywriting Contract

| Element | Copy |
|---------|------|
| Primary CTA | "Buy" (solid purple); secondary "Sell" (purple outline) |
| Trade ticker placeholder / a11y | "Ticker" / "Trade ticker" |
| Trade quantity placeholder / a11y | "Quantity" / "Trade quantity" |
| Empty state heading (positions) | "No positions yet." |
| Empty state body (positions) | "Buy shares with the trade bar to see them here." |
| Empty state heading (heatmap) | "No positions yet." |
| Empty state body (heatmap) | "Your holdings appear here after your first trade." |
| Empty state heading (P&L) | "No portfolio history yet." |
| Empty state body (P&L) | "The chart fills in as snapshots are recorded." |
| Error: invalid ticker | "Enter a ticker of 1-5 letters." |
| Error: invalid quantity | "Enter a quantity above 0 (up to 4 decimals)." |
| Error: insufficient cash | "Insufficient cash: need $X, have $Y" (server detail) |
| Error: oversell | "Cannot sell N TICKER; you hold M" (server detail) |
| Error: network or server | "Could not place the trade. Try again." |
| Destructive confirmation | Sell: none, by design (PLAN.md: no confirmation dialog; simulated money, instant fill). Buy: none |

---

## Registry Safety

| Registry | Blocks Used | Safety Gate |
|----------|-------------|-------------|
| shadcn official | none (Tool: none) | not applicable |
| third-party | none | not applicable |

No new npm dependency (treemap is in-repo code; `lightweight-charts` already added in Phase 2).

---

## Test Hooks (additions)

| test id | Element | Notes |
|---------|---------|-------|
| `total-value` | header total | `$10,000.00` initially after load; numeric parser safe |
| `cash-balance` | header cash | `$10,000.00` initially after load |
| `trade-bar` | trade form | `aria-busy` while pending |
| `trade-ticker` | ticker input | prefilled with selected ticker; `fill()` works |
| `trade-quantity` | quantity input | text input, decimals allowed |
| `buy-button`, `sell-button` | action buttons | `type="button"`, disabled while pending |
| `trade-error` | inline error | present only while an error exists, `role="alert"` |
| `position-row-{TICKER}` | positions row | `role="row"`, `aria-selected`; removed from DOM when sold out |
| `positions-empty` | positions empty state | |
| `heatmap` | heatmap panel | always present |
| `heatmap-cell-{TICKER}` | treemap cell | `data-pnl` = positive / negative / flat |
| `heatmap-empty` | heatmap empty state | |
| `pnl-chart` | P&L panel | `data-points` = number of points; contains the Lightweight Charts canvas |
| `pnl-empty` | P&L empty overlay | when 0 points |

---

## Decisions Log (autonomous)

1. Center column is three rows (chart, trade bar auto, bottom row); bottom row widths 1fr / 1.6fr / 1fr so the six-column positions table fits.
2. Buy is solid `#753991`; Sell is a `#753991` outline with an alpha hover; no new hue. Neither is styled destructive.
3. Quantity is a text input with `inputMode="decimal"` and our own 4-decimal validation; Enter submits Buy.
4. Trade error slot is always 24px high; the `trade-error` element exists only while an error is shown; server `detail` strings are shown verbatim.
5. Heatmap is a squarified treemap of absolutely positioned divs; alpha scale `0.25 + 0.55 * min(|pct|/10, 1)` on up/down tokens; flat is `--color-row-hover`; labels hide under 56x28px and the P&L line hides under 44px height.
6. `data-pnl` thresholds use the rounded displayed value (`+-0.005`), so a displayed `0.00%` is flat.
7. P&L chart is a blue line with a dashed `10000` baseline; snapshots only (no synthetic live tail); one point shows a marker, zero points shows the empty overlay.
8. Header total value is computed client-side per tick; muted when the stream is not connected.
9. Positions sorted by market value descending; P&L and Chg % colored with sign shown in text.
10. Positions rows reuse the watchlist row interaction and selection styling; Price cell reuses `price-cell` flash.
11. Folded fixes: active panel accent underline, add-input refocus on failure (and success), `pl-[10px]` removal, shared chart theme constants, no default AAPL while loading.
12. No new colors, sizes, weights, or dependencies.

---

## Checker Sign-Off

- [ ] Dimension 1 Copywriting: PASS
- [ ] Dimension 2 Visuals: PASS
- [ ] Dimension 3 Color: PASS
- [ ] Dimension 4 Typography: PASS
- [ ] Dimension 5 Spacing: PASS
- [ ] Dimension 6 Registry Safety: PASS

**Approval:** pending

## Checker Clarifications (binding, 2026-10-19)

- **Trade bar height:** strip = 8px top padding + 32px controls + 8px bottom padding = 48px; plus the 24px error slot = 72px total. This supersedes the "40px strip / 64px" line in Layout.
- **Active title underline:** draw it with an inset `box-shadow: inset 0 -2px 0 var(--color-accent)` so the title strip stays exactly 24px (no layout change).
- **Focal point:** the main chart plus the header total value are the primary visual anchors.
- **Buy/Sell labels:** visible text stays "Buy" / "Sell"; `aria-label` "Buy shares" / "Sell shares".
- **Header before data:** `total-value` and `cash-balance` render `--` only until `/api/portfolio` first resolves, then always a `$` number (E2E polls `readNumber`).
