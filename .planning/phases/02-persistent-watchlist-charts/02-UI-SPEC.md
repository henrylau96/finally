---
phase: 2
slug: persistent-watchlist-charts
status: approved
reviewed_at: 2026-10-19
shadcn_initialized: false
preset: none
created: 2026-10-19
---

# Phase 2 - UI Design Contract

> Extends the approved Phase 1 contract (`01-UI-SPEC.md`). All tokens, spacing, typography, and color rules from Phase 1 are inherited unchanged; this document only adds or overrides. Sources: 02-CONTEXT.md (locked), 01-UI-REVIEW.md (fixes folded in), test/e2e/02-watchlist.spec.ts. Autonomous choices are tagged (decision).

---

## Design System

| Property | Value |
|----------|-------|
| Tool | none (no `components.json`; shadcn gate: N per Phase 1, registry gate not applicable) |
| Preset | not applicable |
| Component library | none (React 19.3 + Tailwind 4.3 `@theme` tokens in `globals.css`) |
| Icon library | none; the remove "x" is the text glyph `×` (U+00D7), no icon dependency (decision) |
| Chart library | Lightweight Charts 5.2 (canvas), main chart only; sparklines stay inline SVG |
| Font | Inherited: system sans for UI; monospace + tabular-nums for tickers, prices, chart axis labels |

---

## Spacing Scale

Inherited scale (4, 8, 16, 24, 32, 48, 64). Phase 2 usage:

| Token | Value | Phase 2 usage |
|-------|-------|---------------|
| xs | 4px | Gap between add input and button; chart header gaps |
| sm | 8px | Add-form padding, chart header padding, cell horizontal padding |
| md | 16px | Empty-state padding in chart |
| lg | 24px | Notice slot height; add-form error line height; column header strip |
| xl | 32px | Add-form control height; watchlist row height |
| 2xl | 48px | Header height (unchanged) |

Exceptions:
- Add input and Add button are 32px high (matches row density; desktop-first, no 44px target).
- Remove button hit area is 24px x 24px, sits inside the 32px row (on-scale).
- Selected-row left border is 2px (inherited).

---

## Typography

Inherited: exactly 4 sizes (12 / 14 / 16 / 20), 2 weights (400, 600). No new sizes.

| Phase 2 element | Size | Weight | Notes |
|-----------------|------|--------|-------|
| Add input text and placeholder | 14px | 400 | monospace, uppercase via `text-transform: uppercase` plus value uppercased in state |
| Add button label | 14px | 600 | |
| Inline error / notice text | 12px | 400 | Label size, regular weight (decision: both within the declared 12px size and 400 weight) |
| Remove glyph `×` | 16px | 400 | Heading size, regular weight |
| Chart header ticker | 16px | 600 | Heading role, monospace |
| Chart header last price | 20px | 600 | Display role, monospace tabular-nums |
| Chart axis / crosshair labels | 12px | 400 | monospace (set via Lightweight Charts `fontSize: 12`, `fontFamily` = mono stack) |

---

## Color

Inherited split: 60% `--color-bg` `#0d1117`, 30% `--color-surface` `#161b22` + border `#30363d`, 10% accent `#ecad0a`.

### Panel surfaces (folds in review fix 3)

| Region | Token |
|--------|-------|
| Panel body (watchlist rows, chart area) | `--color-bg` |
| Panel title strip, watchlist column header strip, add-form strip, chart header strip | `--color-surface` |
| Add input background | `--color-bg`, 1px `--color-border` |
| Header bar, chat dock | `--color-surface` (unchanged) |

`Panel.tsx` body changes to `bg-bg`; title strip gets `bg-surface` with a 1px bottom border. ChatDock stays surface.

### Phase 2 color assignments

| Element | Color |
|---------|-------|
| Add button | background `--color-submit` `#753991`, text `--color-text`, hover: brightness +10% (`filter: brightness(1.1)`), disabled: opacity 0.5 (decision: disabled state uses the fixed button, no new color) |
| Inline error text | `--color-down` `#f85149` |
| Remove button | resting `--color-text-muted`; hover/focus `--color-down` (Phase 1 reserved "remove-ticker hover" for Destructive) |
| Selected row | 2px left border `--color-primary` + background `--color-row-hover` `#1c2230` (inherited) |
| Hover row (unselected) | background `--color-row-hover` only, no left border |
| Chart line | `--color-primary` `#209dd7` (Phase 1 reserved the main chart line for blue) |
| Chart fill | vertical gradient `rgba(32,157,215,0.28)` at top to `rgba(32,157,215,0)` at bottom |
| Chart grid | `--color-border` at 50% opacity (`rgba(48,54,61,0.5)`), horizontal and vertical lines |
| Chart crosshair | lines `--color-text-muted`, dashed; label background `--color-surface`, label text `--color-text` |
| Chart axis text | `--color-text-muted` |
| Chart background | transparent over `--color-bg` |

Accent `#ecad0a` reserved for (unchanged from Phase 1): (1) "FinAlly" wordmark, (2) active panel title underline. In Phase 2 the Watchlist panel title and the Main chart panel title keep the accent underline as "active panel" markers; nothing new uses accent. Not used on chart, buttons, or selection.

Selection is not signaled by color alone: the row also has `aria-selected="true"` and the 2px left border.

---

## Layout

Phase 1 grid unchanged. Phase 2 changes inside panels only.

### Watchlist panel (top to bottom)

1. Panel title strip "Watchlist" (surface, 24px).
2. Add form strip (surface, 8px padding, 32px controls, 4px gap): `[ input flex-1 ][ Add 56px ]`.
3. Error slot (fixed 24px high, 12px text, 8px horizontal padding). Always reserved; empty text when there is no error (decision, no layout shift).
4. Notice slot (fixed 24px high, always rendered, see below).
5. Column header strip (24px, surface).
6. Rows (32px each, bg, scrolls internally).

Rows never shift vertically when the error or notice text changes because both slots keep a fixed height.

### Main chart panel

```
+----------------------------------------------+
| MAIN CHART (title strip, surface)            |
+----------------------------------------------+
| AAPL                              $190.42    |  header strip 40px (surface)
+----------------------------------------------+
|                                              |
|   Lightweight Charts area chart (bg)         |
|                                              |
+----------------------------------------------+
```

- Chart header strip is 40px high (8px padding + 24px content), surface background: ticker (16px/600 mono, left), last price (20px/600 mono tabular-nums, right). Last price uses primary text color; day change is not repeated here.
- Chart canvas fills the remaining panel body on `--color-bg`; resize via `ResizeObserver` (autoSize).
- The `main-chart` test id is on the panel body wrapper and carries `data-ticker="{SELECTED}"` (never empty after load; default `AAPL`). Selection of a ticker no longer in the watchlist falls back to the first remaining row, or empty string when the list is empty (decision).

---

## Watchlist Add Form (WATCH-01)

| Property | Contract |
|----------|----------|
| Input | `data-testid="watchlist-add-input"`, `type="text"`, `placeholder="Add ticker, e.g. PYPL"`, `aria-label="Ticker symbol"`, `maxLength=5`, `autocomplete="off"`, `spellcheck=false`, value uppercased on change |
| Button | `data-testid="watchlist-add-button"`, `type="submit"`, label "Add", purple `--color-submit` |
| Submit | The input and button are inside one `<form>`; Enter or button click submits |
| Client validation | Trim then uppercase; must match `^[A-Z]{1,5}$`. Fails: no request, inline error "Enter 1-5 letters, e.g. PYPL." |
| Pending | While the POST is in flight: input and button `disabled`, button label stays "Add", button `aria-busy="true"`, cursor `progress`. Prevents double submit |
| Success | Input cleared, error cleared, row appears via re-fetch of `GET /api/watchlist`, focus returns to the input. Duplicate (HTTP 200 existing row) is treated as success silently (no error, no second row) |
| API error | Inline error below the form, in the fixed error slot, `role="alert"`, `data-testid="watchlist-add-error"`. Input keeps its value so the user can fix it |
| Error copy | 422: "Enter 1-5 letters, e.g. PYPL." Network or 5xx: "Could not add the ticker. Try again." |
| Error clearing | Cleared on next keystroke in the input or on next submit |
| Focus ring | 2px `--color-primary` (inherited `:focus-visible`) |

Input height 32px, padding 0 8px, border 1px `--color-border`, radius 0 (matches flat terminal look; Phase 1 has no rounded corners, decision).

---

## Per-row Remove (WATCH-02)

- Element: `<button type="button" data-testid="watchlist-remove-{TICKER}" aria-label="Remove {TICKER} from watchlist" title="Remove {TICKER}">×</button>`.
- Placement: inside the row, as a new last column of 24px (grid template becomes `72px 1fr 72px 72px 24px`; the Chart column is 64px plus gap as before). Header strip gets an empty 24px cell with `role="columnheader"` and `aria-label="Actions"` (decision).
- Visibility: `opacity: 0` by default; `opacity: 1` on row `:hover`, row `:focus-within`, and the button `:focus-visible`. Transition 100ms opacity, none under reduced motion. The button stays in the tab order (opacity, not `display:none`/`visibility:hidden`), so keyboard users reach it, and Playwright can click it after the row hover (Playwright click hovers the element first; opacity 0 elements are still actionable).
- Touch fallback: under `@media (hover: none)` the button is always `opacity: 1`.
- Click: `stopPropagation` so it does not change the selection. No confirmation (per CONTEXT). The row is removed after the DELETE resolves (204 or 404 both treated as removed) and the list re-fetched. While the DELETE is pending the button is `disabled`.
- If the removed ticker was selected, selection moves to the first remaining row.
- Failure (network): row stays; error text "Could not remove {TICKER}. Try again." appears in the shared error slot.

---

## Row Selection (WATCH-03, UI-06)

| State | Visual |
|-------|--------|
| Default | bg, 1px bottom border, transparent 2px left border (reserves width, no shift) |
| Hover | `--color-row-hover` background, no left border |
| Focus-visible | 2px `--color-primary` outline (inset) |
| Selected | `--color-row-hover` background plus 2px `--color-primary` left border, `aria-selected="true"`. Ticker text weight stays 600 |
| Selected and hover | same as selected (no extra change) |

Hover and selected share the background token by design (Phase 1 contract); the left border and `aria-selected` are what distinguish selected from hover (decision: do not introduce a new color).

Interactions: click, Enter, or Space on a focused row selects it. Space calls `preventDefault` to stop page scroll. Arrow Up/Down moving focus between rows is a nice-to-have, not required (decision: out of scope). Selection is in-memory only.

---

## Table Semantics (review fix)

- Container: `role="grid"` (see below) with `aria-label="Watchlist"`; header strip wrapper `role="rowgroup"` containing a `role="row"` with `role="columnheader"` cells: Symbol, Price, Day %, Chart, and the empty Actions cell.
- Body: `role="rowgroup"`; each row `role="row"`, `tabindex=0`, `aria-selected` true/false; cells `role="cell"` (Symbol, Price, Day %, Chart; remove button in its own `role="cell"`).
- Use `role="grid"` (not `table`) so `aria-selected` on `row` is valid; cells use `role="gridcell"`, header cells `role="columnheader"`, `aria-rowcount` omitted (decision).
- Test ids unchanged: `watchlist-row-{TICKER}`, `price-{TICKER}`.

---

## Notice Slot (review fix 1)

A single always-rendered slot, fixed height 24px (`h-6`, `overflow: hidden`, single line, text truncates with ellipsis, full text in `title`), placed above the column header strip. Content never changes the slot height, so rows do not move.

Precedence (highest first), one message at a time:

| Priority | Condition | Text |
|----------|-----------|------|
| 1 | status `disconnected` | "Price stream closed. Reload the page to retry." |
| 2 | status `reconnecting` (including initial Connecting) | "Reconnecting to price stream. Prices may be stale." |
| 3 | status `connected` and no tick received yet | "Waiting for prices..." |
| 4 | otherwise | empty (slot remains, no text) |

Style: 12px, 400, `--color-text-muted`, 8px horizontal padding. Reconnecting takes precedence over Waiting (per CONTEXT). Slot uses `role="status"` `aria-live="polite"`.

Note: The Phase 1 two-line "Waiting for prices" heading plus body is replaced by this single line (decision, needed to keep a 24px slot).

Watchlist loading state (before `GET /api/watchlist` resolves): rows area shows nothing and the notice slot reads "Loading watchlist..." (decision). If the fetch fails: notice slot reads "Could not load the watchlist. Reload the page." in `--color-down`.

Empty watchlist (all removed): rows area shows centered muted 14px text "No tickers yet. Add one above." (`data-testid="watchlist-empty"`).

---

## Main Chart (UI-05)

### Lightweight Charts options (prescriptive)

```
layout:    { background: { type: 'solid', color: 'transparent' }, textColor: '#8b949e',
             fontSize: 12, fontFamily: <mono stack> }
grid:      { vertLines: { color: 'rgba(48,54,61,0.5)' }, horzLines: { color: 'rgba(48,54,61,0.5)' } }
crosshair: { mode: CrosshairMode.Normal,
             vertLine: { color: '#8b949e', style: LineStyle.Dashed, width: 1, labelBackgroundColor: '#161b22' },
             horzLine: { color: '#8b949e', style: LineStyle.Dashed, width: 1, labelBackgroundColor: '#161b22' } }
rightPriceScale: { borderColor: '#30363d', scaleMargins: { top: 0.1, bottom: 0.1 } }
timeScale: { borderColor: '#30363d', timeVisible: true, secondsVisible: true, rightOffset: 4 }
autoSize: true
```

Note: keep the default TradingView attribution logo on (library license); do not set `attributionLogo: false` (decision).

Series: `AreaSeries` with `lineColor: '#209dd7'`, `topColor: 'rgba(32,157,215,0.28)'`, `bottomColor: 'rgba(32,157,215,0)'`, `lineWidth: 2`, `priceLineVisible: true` (dashed line at last price, line color `#209dd7`), `lastValueVisible: true`, `crosshairMarkerRadius: 4`.

### Data and formatting

- Source: client buffer per ticker, ~1000 points since page load, one point per SSE message; separate from the 120-point sparkline buffer.
- Time axis: UTC seconds from the SSE timestamp (`UTCTimestamp`). Multiple messages in the same second collapse to the latest value (library requires strictly ascending times). Local time zone display via `localization.timeFormatter` (HH:mm:ss, 24-hour).
- Price format: `localization.priceFormatter = (p) => '$' + p.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})`, matching the watchlist format (`$190.42`, thousands separator). Price scale shows 2 decimals; right-hand axis.
- Switching ticker: `setData` with the new ticker's buffer, `timeScale().fitContent()`; subsequent ticks use `series.update()` and do not reset zoom or scroll when the user has panned. Auto-scroll follows real time only when the view is already at the right edge (library default).
- Interactions: crosshair on hover, wheel zoom and drag pan allowed (library defaults). No toolbars, no indicators, no volume.
- Under `prefers-reduced-motion`: no custom animation exists; nothing to disable.

### Chart header

- Left: selected ticker (16px/600 mono); right: last price (20px/600 mono tabular-nums) from the live quote, `--` when no price yet. Element ids: `main-chart-ticker`, `main-chart-price`.
- Last price has no flash (the watchlist cell owns flash).
- When status is not `connected`, last price text switches to `--color-text-muted` (consistent with the Phase 1 stale rule).

### States

| State | Condition | Display |
|-------|-----------|---------|
| Empty (not enough points) | fewer than 2 points buffered for the selected ticker | Chart canvas is not created data-wise (no series data); centered overlay in the chart body, muted 14px: "Collecting price data for {TICKER}..." with a second 12px muted line "The chart fills in as prices stream." (`data-testid="main-chart-empty"`, `role="status"`). Overlay is removed as soon as 2 points exist. Grid may render behind the overlay |
| No selection | watchlist empty | Centered muted text "Add a ticker to see its chart." |
| Stream offline | status not connected | Chart keeps the last data, no change; the watchlist notice carries the message |
| Normal | 2+ points | Area chart |

The Phase 1 placeholder copy "Select a ticker to see its chart. Coming soon." is removed.

---

## Interaction Contract (additions)

| Interaction | Behavior |
|-------------|----------|
| Page load | Fetch `GET /api/watchlist`; render rows; open SSE (as Phase 1); default selection AAPL (first row if AAPL is absent); chart shows empty overlay until 2 ticks |
| Add ticker | Validate, POST, pending state, re-fetch, row appears at the end of the list (list order = server order, `added_at` ascending), price fills when the first tick arrives (`--` until then) |
| Remove ticker | Click ×, DELETE, re-fetch, row disappears; sparkline and chart buffers for that ticker are dropped |
| Select ticker | Click, Enter, or Space on row; chart swaps data and header; `data-ticker` updates |
| Tab order | Add input, Add button, then per row: row, remove button; chat toggle last |
| Esc in add input | Clears the input and the error (decision) |

---

## Copywriting Contract

| Element | Copy |
|---------|------|
| Primary CTA | "Add" (watchlist add; purple submit button) |
| Add input placeholder | "Add ticker, e.g. PYPL" |
| Add input label (a11y) | "Ticker symbol" |
| Remove button label (a11y) | "Remove {TICKER} from watchlist" |
| Empty state heading (watchlist) | "No tickers yet." |
| Empty state body (watchlist) | "Add one above to start streaming prices." (rendered together as "No tickers yet. Add one above.") |
| Empty state (chart, collecting) | "Collecting price data for {TICKER}..." / "The chart fills in as prices stream." |
| Empty state (chart, no ticker) | "Add a ticker to see its chart." |
| Error: invalid ticker | "Enter 1-5 letters, e.g. PYPL." |
| Error: add failed | "Could not add the ticker. Try again." |
| Error: remove failed | "Could not remove {TICKER}. Try again." |
| Error: watchlist load failed | "Could not load the watchlist. Reload the page." |
| Notices | "Waiting for prices..." / "Reconnecting to price stream. Prices may be stale." / "Price stream closed. Reload the page to retry." / "Loading watchlist..." |
| Destructive confirmation | Remove ticker: none, by design (PLAN.md and CONTEXT: no confirmation; low stakes, instantly re-addable) |

---

## Registry Safety

| Registry | Blocks Used | Safety Gate |
|----------|-------------|-------------|
| shadcn official | none (Tool: none) | not applicable |
| third-party | none | not applicable |

npm dependency added: `lightweight-charts` 5.2 (official TradingView package, Apache-2.0). Not a UI registry; no vetting gate applies.

---

## Test Hooks (additions)

| test id | Element | Notes |
|---------|---------|-------|
| `watchlist-add-input` | add input | fill with lowercase is uppercased |
| `watchlist-add-button` | Add button | submit; disabled while pending |
| `watchlist-add-error` | inline error | `role="alert"`, only present when an error exists |
| `watchlist-remove-{TICKER}` | per-row remove button | clickable (opacity based reveal) |
| `watchlist-row-{TICKER}` | row | now `role="row"` with `aria-selected` |
| `watchlist-empty` | empty list message | |
| `main-chart` | chart panel body | `data-ticker` = selected ticker |
| `main-chart-ticker`, `main-chart-price` | chart header | |
| `main-chart-empty` | collecting overlay | present when under 2 points |

---

## Decisions Log (autonomous)

1. Remove glyph is `×` text, no icon library.
2. Selected and hover share `#1c2230`; left border plus `aria-selected` distinguish selection.
3. Chart line is blue `#209dd7` per Phase 1 reservation; accent stays out of the chart.
4. Fixed 24px notice slot and 24px error slot always rendered; Phase 1 two-line notice becomes one line.
5. `role="grid"` / `gridcell` so `aria-selected` on rows is valid.
6. Remove button hidden via opacity (still tabbable) and always visible on `hover: none` devices.
7. Flat zero-radius controls; no new colors, sizes, or weights introduced.
8. Keep Lightweight Charts attribution logo on for license compliance.
9. Duplicate add (200) is silent success; delete 204 and 404 both remove the row.

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

These resolve ambiguities flagged by the UI checker and take precedence over conflicting lines above.

- **Watchlist grid template:** exactly `72px 1fr 72px 72px 24px` (Symbol, Price, Day %, Chart 64px sparkline inside a 72px column, Remove). Column gap stays 8px.
- **Size exceptions (multiples of 4, justified):** 40px chart header (fits the 20px price line plus 8px padding top/bottom with a 1px border); 56px Add button (fits "Add" at 14/600 with 16px side padding); 72px fixed columns (fit `$1,234.56` / `+12.34%` at 14px tabular-nums); 24px remove column (24px hit area).
- **Cell roles:** container `role="grid"`, header row cells `role="columnheader"`, body cells `role="gridcell"` everywhere.
- **Notice slot precedence (single 24px line, highest first):** 1. "Could not load the watchlist..." (GET failed) 2. disconnected 3. reconnecting 4. "Loading watchlist..." 5. "Waiting for prices" 6. empty-watchlist copy.
- **Add button:** visible label stays "Add" (test-id contract); `aria-label="Add ticker"`.
