# Phase 3 - UI Review

**Audited:** 2026-10-19
**Baseline:** 03-UI-SPEC.md (including binding Checker Clarifications), inheriting 01/02-UI-SPEC.md
**Screenshots:** not captured (code-only audit; no Playwright MCP, no server started)

Out of scope by instruction: chat dock placeholder (Phase 4), narrow/tablet layout (Phase 6, UI-13).

---

## Pillar Scores

| Pillar | Score | Key Finding |
|--------|-------|-------------|
| 1. Copywriting | 4/4 | All contract strings, aria-labels and error copy exact |
| 2. Visuals | 3/4 | Heatmap has no selected-cell styling; heatmap cells use `role="img"` while interactive |
| 3. Color | 3/4 | Token usage and heatmap scale correct; up/down rgba literals duplicated in Heatmap.tsx and TradeBar.tsx |
| 4. Typography | 4/4 | Exactly 12/14/16/20 and weights 400/600 |
| 5. Spacing | 3/4 | On-scale throughout; trade bar is 74px not 72px; watchlist header still not sticky |
| 6. Experience Design | 2/4 | Enter-to-Buy likely does not fire (no submit button, two text inputs); selection jumps after selling an unwatched ticker |

**Overall: 19/24**

---

## Top 3 Priority Fixes

1. **Enter does not submit Buy (WARNING, likely functional defect)** - `TradeBar.tsx:90,100` make both buttons `type="button"` and the form has two text inputs. Under the HTML implicit-submission rule, a form with no submit button only submits on Enter when it has at most one blocking field. With ticker and quantity inputs, Enter should do nothing, so `onSubmit` (`:47`) is probably dead code. The contract says "Enter in either input submits Buy". Not confirmed in a browser. Fix: add `onKeyDown` Enter handling on both inputs that calls `submit("buy")`, or render a visually hidden `type="submit"` button. Add an E2E for Enter.
2. **Selection can silently jump after a sell (WARNING)** - Contract (Positions, Sold-out): "if it was selected the selection stays (chart still shows it)". `Terminal.tsx:27-29` validates `selected` against watchlist tickers plus current positions only. Sell a whole position in a ticker that is not on the watchlist and the effect resets selection to AAPL, changing the main chart and the trade ticker prefill. Fix: keep `selected` unless it was never valid (for example only reset when `selected` is empty or removed from the watchlist by the user).
3. **Heatmap cell selection is invisible and semantics are wrong (WARNING)** - `Heatmap.tsx:46` writes `data-selected` but no style reads it (`grep data-selected` finds one hit). Watchlist and positions rows show a 2px primary left border, so the shared-selection model has no heatmap feedback. Also the cells are `role="img"` with `tabIndex=0`, click and key handlers (`:47-56`); screen readers announce a non-interactive image. Fix: add `data-[selected=true]:outline outline-primary -outline-offset-2` (or a 2px inset primary shadow), and use `role="button"` with `aria-pressed={selected}` (keep the `aria-label`).

Further items below (token duplication, 2px trade bar overshoot, price cell inset, header tabular-nums).

---

## Detailed Findings

### Pillar 1: Copywriting (4/4)
- Trade bar: placeholders "Ticker" / "Quantity", aria-labels "Trade ticker" / "Trade quantity", "Buy shares" / "Sell shares" (`TradeBar.tsx:56,57,74,75,93,103`). Visible labels "Buy" / "Sell".
- Client errors exact (`TradeBar.tsx:5-6`); 422 mapping and server `detail` passthrough for 400, generic "Could not place the trade. Try again." (`usePortfolio.ts:95-111`). Error element has `title` for truncation.
- Empty states exact for Positions (`PositionsTable.tsx:29-30`), Heatmap (`Heatmap.tsx:33-34`), P&L (`PnlChart.tsx:78-79`).
- Nit: ticker and quantity inputs carry `uppercase`, so placeholders render as "TICKER" and "QUANTITY" (same pattern flagged in Phase 2). Contract-faithful for the value; consider limiting the transform to the ticker's value.

### Pillar 2: Visuals (3/4)
- Phase 2 fix 1 landed: `Panel.tsx:21` draws the accent underline with `shadow-[inset_0_-2px_0_var(--color-accent)]`, exactly per the Checker Clarification (title strip stays 24px). Passed via `active` on Watchlist and Main chart only (`Terminal.tsx:39`); Heatmap/Positions/P&L do not.
- Layout matches: center `grid-rows-[1.4fr_auto_1fr]`, bottom row `1fr / 1.6fr / 1fr` with `minmax(0,...)` (`Terminal.tsx:38,43`). Chart plus header total value are the focal anchors (20px/600 total, chart header).
- WARNING: no selected style on heatmap cells (fix 3). Hover outline exists (`Heatmap.tsx:58`).
- Heatmap labels follow the min-size rules: hidden under 56x28, P&L line hidden under 44 height (`:60-64`); `title` and `aria-label` expose the data for hidden labels. Cells get `border border-bg` for the 2px gap.
- Heatmap flat state uses `--color-row-hover`; `fill()` derives its state from `pnlState`, so `0.00%` is always flat. Good.
- Minor: Positions Price cell uses `PriceCell` with `px-1` (`PriceCell.tsx:41`), so the price text sits 4px inside the right edge relative to the Avg cost and P&L columns. Visible misalignment of the right edge in a right-aligned numeric table. Fix: `-mr-1` on the wrapper or a prop to drop padding.
- Needs human review (no screenshots): treemap label legibility on the 0.80 alpha green over `#0d1117`; flash highlight appearance on positions price pill.

### Pillar 3: Color (3/4)
- Accent only on wordmark and the two active panel underlines. Not used on trade buttons, P&L, or heatmap. Per contract.
- Buy solid `bg-submit` with `hover:brightness-110`, `disabled:opacity-50`; Sell outline `border-submit` with alpha hover; error `text-down`. P&L text colors via `COLORS` map (up/down/muted-for-flat). Header total muted when not connected (`Header.tsx:15`).
- Phase 2 fix 4 landed: hex literals live in `lib/chartTheme.ts` and are shared by both charts; no hex literals remain in components.
- WARNING (minor): `Heatmap.tsx:13` hardcodes `rgba(63,185,80,...)` / `rgba(248,81,73,...)` and `TradeBar.tsx:106` hardcodes `rgba(117,57,145,0.2)`. These duplicate `--color-up`, `--color-down`, `--color-submit`; a token change would desync. Spec explicitly allows alpha derivation, but `color-mix(in srgb, var(--color-up) X%, transparent)` would keep a single source.
- P&L line uses `CHART.primary`; baseline dashed `CHART.muted`. Correct.

### Pillar 4: Typography (4/4)
- Census over `src`: `text-xs` x15, `text-sm` x13, `text-base` x3, `text-xl` x2; only `font-semibold` (x17) plus default 400. No new sizes or weights.
- Heatmap ticker `text-sm font-semibold font-mono`, pct `text-xs font-mono tabular-nums`. Positions headers `text-xs font-semibold uppercase tracking-[0.05em]`, rows `text-sm`, ticker semibold. All per table.
- Minor: Header total (`Header.tsx:15`) and cash (`:22`) are `font-mono` without `tabular-nums` though the spec lists it. Harmless in a monospace stack but contract-visible; add the class.

### Pillar 5: Spacing (3/4)
- On-scale: trade controls `h-8`, buttons `w-14`, inputs `w-20` / `w-24`, `gap-1 p-2`, error slot `h-6 px-2`, positions header `h-6` sticky, rows `h-8`, grid `64px minmax(56px,1fr) 80px 80px 80px 72px gap-2 px-2` with `border-l-2` reserved. Heatmap `p-2`. Exact match to contract.
- Phase 2 fix 3 landed: `pl-[10px]` is gone; watchlist header uses `px-2` plus `border-l-2 border-l-transparent` (`Watchlist.tsx:76`).
- WARNING (minor): trade bar strip is `border-y` + 48px + 24px slot = 74px; clarification says 72px total. Contract wording says "1px border top and bottom", so the two statements conflict; 2px overshoot is cosmetic but should be reconciled (use `box-border h-12` on the strip or drop the bottom border).
- WARNING (minor, Phase 2 carry-over): watchlist header strip is still not sticky; positions header is. Inconsistent.
- Only arbitrary values: `w-[360px]` (dock, inherited) and `tracking-[0.05em]` (spec).

### Pillar 6: Experience Design (2/4)
- BLOCKER-adjacent WARNING: Enter-to-Buy likely dead (fix 1). Mouse and Tab flows are intact, so task completion is not blocked.
- WARNING: selection reset after selling an unwatched ticker (fix 2).
- Good: pending state disables inputs and buttons, sets `aria-busy`, `cursor-progress`; focus returns to quantity after success and failure (`TradeBar.tsx:39`); error clears on keystroke; Esc clears quantity and error; WR-03 regex rejects hex/exponent/trailing dot, WR-04 stable position order (`derivePositions` sorts by fetched market value so ticks do not reorder). Out-of-order portfolio responses guarded by `seq` (`usePortfolio.ts:77`); failure paths re-fetch so displayed cash is current (WR-01 UI part).
- Good: loading states show nothing (no empty-state flash) because `rows` is `null` until the first response; P&L chart keeps previous data on refetch failure; 30s poll plus refetch on `version`.
- Minor: Positions loading renders the column header strip with an empty body (`PositionsTable.tsx:33`), spec says "body empty" so acceptable.
- Minor: Esc handling exists only on the quantity input; a stale error after editing ticker is cleared by keystroke, fine.
- Minor: Phase 2 fix 2 (add-input refocus) landed (`WatchlistAddForm.tsx:26` is before the error return). Fix 5 landed (selection starts `""`).
- Registry audit: shadcn not initialized, no third-party registries. Skipped.

---

## Phase 2 Review Fix Verification

| Fix | Status |
|-----|--------|
| Accent active-panel underline | Landed (inset shadow, 24px strip preserved) |
| Add input refocus after failed add | Landed |
| `pl-[10px]` | Landed |
| Chart hex literals consolidated | Landed (`chartTheme.ts`) |
| Default AAPL while loading | Landed (selection starts empty) |
| Placeholder centering (heatmap/positions/P&L) | Landed (`flex h-full items-center justify-center`) |
| Watchlist header sticky | Not landed (minor) |

---

## Files Audited
- frontend/src/app/globals.css
- frontend/src/components/Header.tsx, Heatmap.tsx, Panel.tsx, PnlChart.tsx, PositionsTable.tsx, PriceCell.tsx, Terminal.tsx, TradeBar.tsx, WatchlistAddForm.tsx, ChatDock.tsx (scope only), Watchlist.tsx (grep)
- frontend/src/lib/chartTheme.ts, format.ts, portfolio.ts, usePortfolio.ts, useSize.ts
- .planning/phases/03-trading-portfolio/03-UI-SPEC.md, 03-REVIEW-FIX.md; .planning/phases/02-persistent-watchlist-charts/02-UI-REVIEW.md
