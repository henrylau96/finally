# Phase 2 - UI Review

**Audited:** 2026-10-19
**Baseline:** 02-UI-SPEC.md (including binding Checker Clarifications), inheriting 01-UI-SPEC.md
**Screenshots:** not captured (code-only audit; no Playwright MCP, no server started)

Out of scope by instruction: heatmap/positions/P&L/chat placeholders, `--` header values, tablet chat-dock auto-collapse (Phase 6, UI-13).

---

## Pillar Scores

| Pillar | Score | Key Finding |
|--------|-------|-------------|
| 1. Copywriting | 4/4 | Every contract string present and exact; notice precedence matches clarifications |
| 2. Visuals | 3/4 | Accent "active panel" title underline still missing (spec'd for Watchlist and Main chart); two Phase 1 nits unfixed |
| 3. Color | 3/4 | Surface/bg inversion fixed; second accent use still absent; chart hex literals duplicate tokens |
| 4. Typography | 4/4 | Exactly 12/14/16/20 and weights 400/600; chart fonts per spec |
| 5. Spacing | 3/4 | Grid, 24px slots, 32px controls all per contract; `pl-[10px]` persists; center column crushed below ~1000px |
| 6. Experience Design | 3/4 | Strong state coverage and a11y; focus is lost after a failed add; stale-state signal is weak in chart |

**Overall: 20/24**

---

## Top 3 Priority Fixes

1. **Accent "active panel" title underline not implemented (WARNING)** - 02-UI-SPEC.md Color says the Watchlist and Main chart panel titles keep the accent underline. `Panel.tsx:19` has only `border-b border-border`, and `grep accent` finds one use (`Header.tsx:7` wordmark). This was Phase 1 review warning 1 and the spec claims it is "unchanged", but it never landed. Fix: add an optional `active` prop to `Panel` that swaps the title border to `border-b-2 border-accent`; pass it from `Watchlist.tsx:51` and the Main chart panel (`Terminal.tsx:31`).
2. **Focus is lost after a failed add (WARNING)** - `WatchlistAddForm.tsx:43` disables the input while pending, which drops focus. Refocus only happens on success (`:28`); on error (`:26`) it returns early, so the keyboard user lands on `body` and must tab back to correct the typo. Spec says "Input keeps its value so the user can fix it". Fix: move `setTimeout(() => input.current?.focus())` before the error return, or use a `finally`.
3. **Center column and chart unusable on narrow widths (WARNING; dock collapse itself is Phase 6)** - `Terminal.tsx:28` is `minmax(320px,28%) 1fr auto` with a fixed 360px dock. At 768px about 48px remains for the chart and the 3-up row (`Terminal.tsx:34`). The chart is now a real component, so it clips visibly. Fix: give the center column `minmax(0,1fr)` with a sensible min width, and cap the dock with `max-lg:w-12` so it degrades before Phase 6 adds the proper logic. Also fix the lingering Phase 1 nit: replace `pl-[10px]` (`Watchlist.tsx:76`) with `pl-2` plus a matching `border-l-2 border-transparent` on the header row.

Further minor items: see findings below (chevron alignment, placeholder vertical centering, chart hex literals, default `AAPL` shown while loading).

---

## Detailed Findings

### Pillar 1: Copywriting (4/4)
- Add form: placeholder "Add ticker, e.g. PYPL", `aria-label="Ticker symbol"`, button "Add" with `aria-label="Add ticker"` (`WatchlistAddForm.tsx:37,38,59`). Matches clarifications.
- Errors exact: "Enter 1-5 letters, e.g. PYPL." (`WatchlistAddForm.tsx:5`, `useWatchlist.ts:47`), "Could not add the ticker. Try again.", "Could not remove {T}. Try again.", "Could not load the watchlist. Reload the page." (`Watchlist.tsx:16`).
- Notice precedence (`Watchlist.tsx:10-22`): load error, disconnected, reconnecting, loading, waiting. Exactly the binding order from Checker Clarifications. Phase 1 finding "Waiting shown instead of reconnecting" is fixed.
- Chart: "Collecting price data for {T}..." / "The chart fills in as prices stream." / "Add a ticker to see its chart." (`MainChart.tsx:113-124`). Empty watchlist "No tickers yet. Add one above." (`Watchlist.tsx:104`). Remove label "Remove {T} from watchlist" with title.
- Nit: because the input is `uppercase`, the placeholder renders as "ADD TICKER, E.G. PYPL". The spec asks for uppercase text-transform, so this is contract-faithful; consider scoping the transform to the value only if it looks shouty in screenshots.

### Pillar 2: Visuals (3/4)
- WARNING: accent title underline missing (fix 1). Accent is used once across the app.
- WARNING (Phase 1 carry-over): placeholder paragraphs are top-aligned (`Terminal.tsx:13` `p-4 text-center`, `ChatDock.tsx:32`); chevron in collapsed rail is left-aligned because `ChatDock.tsx:15` uses `justify-between` with one child. Not in the Phase 2 scope list, but the review fixes were supposedly folded in.
- Good: clear focal hierarchy in chart header (16px/600 ticker left, 20px/600 price right, 40px strip). Selected row has 2px primary left border plus `aria-selected`; hover has no border so the two states are distinguishable. Remove button is revealed by opacity (hover, focus-within, focus-visible) and forced visible under `hover: none` (`globals.css:67`, `WatchlistRow.tsx:78`). `×` is a labelled text button, no icon dependency.
- Chart empty overlay is `bg-bg` full-bleed (`MainChart.tsx:121`), so the grid does not show behind it (spec says it "may"). Acceptable; it also blocks crosshair interaction with the single point, which is desired.
- Good: Lightweight Charts attribution left on; area gradient, dashed crosshair, price line, and `$1,234.56` formatter match the options block verbatim.
- Subjective, needs human review: the flash highlight on the inline price span is still a small pill rather than the full cell.

### Pillar 3: Color (3/4)
- Panel body now `bg-bg` with `bg-surface` title strip, add-form strip, chart header, dock, header (`Panel.tsx:16-19`, `WatchlistAddForm.tsx:32`, `MainChart.tsx:99`). Phase 1 inversion is fixed; ratio is now close to 60/30.
- Add button `bg-submit` with `hover:brightness-110` and `disabled:opacity-50`; error text `text-down`; remove button muted to `hover:text-down`. All per contract.
- WARNING: accent usage count is 1 (wordmark); the contract promises a second (active-panel underline). See fix 1.
- WARNING (minor): `MainChart.tsx:21-44` hardcodes 8 hex/rgba literals (`#8b949e`, `#161b22`, `#30363d`, `#209dd7`, rgba variants). Values are correct, but they duplicate the `@theme` tokens, so a token change will silently desync the chart. Canvas cannot read CSS vars directly; read them once via `getComputedStyle` or export a shared constants module.
- Row hover/selected share `#1c2230` by design.

### Pillar 4: Typography (4/4)
- Class census across `src`: `text-xs` x9, `text-sm` x5, `text-base` x3, `text-xl` x2; weights: only `font-semibold` (x12) plus default 400. Exactly 12/14/16/20 and 2 weights. No new sizes introduced in Phase 2.
- Add input `font-mono text-sm uppercase`, button `text-sm font-semibold`, errors `text-xs`, remove glyph `text-base`, chart header 16/20 mono semibold with `tabular-nums` on price; chart axis `fontSize: 12` with the mono stack. All per table.
- Minor: chart header ticker lacks `tabular-nums`, which is irrelevant for a symbol.

### Pillar 5: Spacing (3/4)
- Grid template `72px 1fr 72px 72px 24px` with `gap-2` in both header and rows (`Watchlist.tsx:7`, `WatchlistRow.tsx:51`), per the binding clarification. Rows `h-8`, header strip `h-6`, error slot `h-6`, notice slot `h-6 overflow-hidden truncate`, form controls `h-8`, button `w-14`, chart header `h-10`, remove `h-6 w-6`, form `gap-1 p-2`. Everything on-scale or in the documented exceptions. Layout-shift defect from Phase 1 is fixed: both slots are always rendered at fixed height.
- WARNING: `pl-[10px]` (`Watchlist.tsx:76`) still off-scale and coupled to the row's 2px border.
- WARNING: narrow-width crush (fix 3). Also, the watchlist header strip is not sticky, so it scrolls with rows when the list overflows.
- Minor: `Watchlist.tsx:70` grid is not inside the scroll container separately from the add form, so on short viewports the add form and slots scroll away with rows (spec says rows scroll internally, i.e. only rows). Body `overflow-auto` is on the whole panel.

### Pillar 6: Experience Design (3/4)
- Good state coverage: loading ("Loading watchlist..."), load error, empty list, pending add (input+button disabled, `aria-busy`, progress cursor), pending remove (button disabled), duplicate as silent success, 404 on delete as success, Esc to clear, error clears on keystroke, selection fallback to first row (`Terminal.tsx:20-24`), stale last-price muted when not connected (`MainChart.tsx:105`), out-of-order reloads guarded by `seq` (`useWatchlist.ts:22,28`). Chart cleanup resets sync refs on teardown. No destructive confirmation, by design.
- Good a11y: `role=grid` with rowgroup/row/columnheader/gridcell, `aria-selected`, Enter and Space select with `preventDefault`, remove `onKeyDown` stopPropagation so Space on the button does not select, `role="alert"` on error, `role="status"` on notice and chart overlay.
- WARNING: focus lost after failed add (fix 2).
- WARNING: while loading, `selected` defaults to `"AAPL"` (`Terminal.tsx:19`), so the chart header shows AAPL and "Collecting price data for AAPL" even when AAPL is not in the list until the fallback effect runs. Brief, but wrong on a persisted watchlist that removed AAPL.
- Minor: the remove failure error appears in the shared error slot, which is also cleared by the next keystroke in the add input, so a failed remove can vanish unnoticed. Acceptable per spec ("shared error slot").
- Minor: error slot is `aria-live` via `role="alert"` only when it mounts; fine.
- Registry audit: shadcn not initialized, no third-party registries. Skipped.

---

## Phase 1 Review Fix Verification

| Fix | Status |
|-----|--------|
| Layout shift from notice | Landed (fixed 24px slots) |
| Panel body bg / title surface | Landed |
| Table semantics, aria-selected, Space key | Landed |
| Reconnecting vs Waiting precedence | Landed |
| Tablet dock collapse | Deferred to Phase 6 (instructed) |
| Accent active-panel underline | NOT landed |
| `pl-[10px]` | NOT landed |
| Placeholder vertical centering / chevron centering | NOT landed |

---

## Files Audited
- frontend/src/app/globals.css, layout.tsx, page.tsx
- frontend/src/components/ChatDock.tsx, ConnectionStatus.tsx, Header.tsx, MainChart.tsx, Panel.tsx, PriceCell.tsx, Sparkline.tsx, Terminal.tsx, Watchlist.tsx, WatchlistAddForm.tsx, WatchlistRow.tsx
- frontend/src/lib/format.ts, usePriceStream.ts, useWatchlist.ts
- .planning/phases/02-persistent-watchlist-charts/02-UI-SPEC.md, 02-0[1-4]-PLAN/SUMMARY, 01-UI-REVIEW.md
