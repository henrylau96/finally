# Phase 1 - UI Review

**Audited:** 2026-10-19
**Baseline:** 01-UI-SPEC.md (approved design contract)
**Screenshots:** not captured (code-only audit; no Playwright MCP, no server started)

Out-of-scope by instruction: "Coming soon" placeholders and `--` header values are not scored as defects.

---

## Pillar Scores

| Pillar | Score | Key Finding |
|--------|-------|-------------|
| 1. Copywriting | 4/4 | All contract strings present and exact; only nit is un-specced "Assistant" dock title |
| 2. Visuals | 3/4 | Missing accent title underline, placeholders top-aligned, watchlist rows jump when notice disappears |
| 3. Color | 3/4 | Tokens correct, but 60/30/10 is inverted (surface dominates, bg barely visible); second accent use missing |
| 4. Typography | 4/4 | Exactly 4 sizes (12/14/16/20) and 2 weights; mono + tabular-nums as specified |
| 5. Spacing | 3/4 | On-scale throughout; off-scale `pl-[10px]`; center column collapses at tablet width |
| 6. Experience Design | 3/4 | Tablet-collapsed dock not implemented; layout shift; weak table semantics; no selected-state a11y |

**Overall: 20/24**

---

## Top 3 Priority Fixes

1. **Watchlist rows shift vertically when the stream status notice appears/disappears** - `Watchlist.tsx:42` renders `<Notice>` in normal flow above the header strip and rows. On every load, the "Waiting for prices" block (about 2 lines, roughly 42px) vanishes on the first tick and all 10 rows jump up. The same happens on every reconnect. Fix: reserve a fixed-height slot (for example `min-h-6`), or render the notice below the rows or as an overlay.
2. **Chat dock is not collapsed on tablet; center column is crushed** - `ChatDock.tsx:6` hard-codes `useState(false)`. The spec says the dock starts collapsed under 1024px. At 768px the grid `minmax(320px,28%) 1fr 360px` leaves about 56px for the center column, so the 3-up bottom panels are unusable. Fix: initialise `collapsed` from `matchMedia("(max-width: 1023px)")` in an effect. A CSS-only alternative is a `max-lg:` width on the aside.
3. **Surface/background ratio inverted (Color 60/30/10)** - `Panel.tsx:14` and `ChatDock.tsx:12` paint every panel `bg-surface` (#161b22). The spec says the watchlist/table body and main chart area, which are the largest areas, use `--color-bg` (#0d1117), with surface reserved for headers, panel title strips and the dock. As built, surface is the dominant colour and `bg` only shows in the 8px gutters. Fix: make the panel body `bg-bg` and give the title strip `bg-surface`.

---

## Detailed Findings

### Pillar 1: Copywriting (4/4)
- Header and metadata match the contract: `layout.tsx:6` title "FinAlly - AI Trading Workstation"; `Header.tsx:7` "FinAlly".
- Connection labels (`ConnectionStatus.tsx:9-13`) cover Live, Offline, Reconnecting and the initial Connecting. `hasConnected` is used to tell the two reconnecting cases apart.
- Watchlist notices (`Watchlist.tsx:11-22`) match the contract word for word: "Waiting for prices", "Prices appear as soon as the stream connects. No action needed.", "Reconnecting to price stream. Prices shown may be stale.", and "Price stream closed. Reload the page to retry."
- Placeholder strings in `Terminal.tsx:24-34` and `ChatDock.tsx:32` match the copy table.
- Nit (WARNING-level only): the dock title "Assistant" (`ChatDock.tsx:17`) and the panel titles "Main chart", "Heatmap", "Positions" and "P&L" are not in the contract. They are reasonable.
- Nit: the tooltip reads "Price stream: reconnecting" during the initial Connecting phase, which is consistent with the contract.

### Pillar 2: Visuals (3/4)
- WARNING: the selected-panel title underline in accent yellow, reserved by the spec, is not implemented. Accent appears only on the wordmark (`Header.tsx:7`). The "selected" cue in the watchlist is only a 2px blue left border; the selected and hover backgrounds are identical (`WatchlistRow.tsx:32`), so a hovered row looks selected apart from the border.
- WARNING: the layout shift described in fix 1 is a visible defect on every page load.
- WARNING: the placeholder text is only horizontally centered (`text-center p-4`, `Terminal.tsx:11`, `ChatDock.tsx:32`). The spec calls for it to be centered in the panel, and it currently sits at the top.
- WARNING: when the dock is collapsed to the 48px rail, the chevron button is left-aligned (`justify-between` with a single child, `ChatDock.tsx:15`) rather than centered in the rail.
- The price flash is on an inline `span` (`PriceCell.tsx:38`) with `px-1`. The highlight is a small pill hugging the text (about 21px high) rather than a full 32px cell. This is acceptable and matches "price cell only", but it looks lighter than a terminal cell flash. This is a subjective item to check against screenshots.
- Good: the focal hierarchy is clear (Display total value, mono tickers at 600 weight, muted uppercase labels). The icon-only chevron has an aria-label. The sparkline has `aria-hidden`.

### Pillar 3: Color (3/4)
- Tokens in `globals.css:4-15` match the contract exactly. No hardcoded hex in TSX; the sparkline uses `var(--color-up/down)`. The only rgba values are the specced flash colors. No pure black or white.
- Accent usage: 1 element (the wordmark). Within contract, though the second reserved use is missing. Purple `submit` is defined and unused, as specced.
- WARNING: the 60/30/10 inversion described in fix 3. Class counts: `bg-surface` appears in Panel, ChatDock and Header; `bg-bg` appears only on `body`.
- Day % colors follow the sign. They fall to muted when offline or when the value is 0, per contract. Price text stays primary and only its background flashes, per contract.
- Muted text `#8b949e` on `#161b22` is about 5.6:1, so it passes 4.5:1.

### Pillar 4: Typography (4/4)
- Sizes in use: `text-xs` (12), body 14 (`globals.css:23`), `text-base` (16, wordmark), `text-xl` (20, total value). That is exactly the 4 declared. Weights are 400 and `font-semibold` only.
- Labels use `uppercase tracking-[0.05em] text-xs font-semibold text-text-muted` consistently (Panel, Header, Watchlist headers, ChatDock).
- Tickers are mono 600. Prices and Day % are mono with tabular-nums (`globals.css:48`, `WatchlistRow.tsx:41`).
- Nit: the connection label (`ConnectionStatus.tsx:32`) is 12px/600 muted but not uppercase. This is fine, since the contract calls it a status text Label.

### Pillar 5: Spacing (3/4)
- Scale adherence is good: `p-2`, `gap-2`, `h-12` header, `h-8` rows, `h-6` header strip, `w-12` rail, `w-[360px]` dock, `h-2 w-2` dot, `gap-6`, and a 64x20 sparkline. All are on the 4px grid.
- WARNING: `pl-[10px]` (`Watchlist.tsx:45`) is an arbitrary off-scale value, used to compensate for the row's 2px left border. A transparent 2px border plus `px-2` (rows) vs `px-2 pl-[10px]` (header) is a fragile coupling. Use `pl-2` plus a matching `border-l-2 border-transparent`.
- WARNING: at tablet width the center column is about 56px wide (see fix 2), so the bottom row's three-column split is unusable. Layout does not cause page scroll (`overflow-hidden`) but content is clipped.
- WARNING: with a short viewport the watchlist header strip scrolls away with the rows. It is not sticky.

### Pillar 6: Experience Design (3/4)
- Good: the stream state machine matches the contract (`usePriceStream.ts:37-42`). Flash direction is derived from the last rendered price. Flashes stop when not live (`PriceCell.tsx:24`). Stale values go muted. Rows render before the first tick with `--`. The EventSource is cleaned up. `prefers-reduced-motion` is handled for the pulse and the flash. There is a global focus ring and rows are keyboard-focusable with Enter.
- WARNING: tablet default-collapsed dock is missing (fix 2).
- WARNING: when status is `reconnecting` and no quotes have arrived yet, the notice shows "Waiting for prices" and never the reconnect or closed-stream message (`Watchlist.tsx:13` is checked before `:21`). A user whose stream dropped before the first tick gets no stale/reconnecting hint beyond the header dot.
- WARNING: table semantics are incomplete. `role="table"` sits on the section (`Watchlist.tsx:41`) and contains a bare `<p>` notice. Rows use `role="row"` but the spans have no `cell` or `columnheader` roles. The selected row has no `aria-selected` or `aria-current`, so screen-reader users cannot tell which ticker is selected.
- WARNING: only Enter selects a row; Space does not. This is minor.
- Disabled, loading and destructive states are N/A for Phase 1. There is no error boundary around JSON.parse in `onmessage` (`usePriceStream.ts:44`). A malformed event would throw inside the handler. This is acceptable under the project's "no defensive programming" rule.

---

## Registry Safety
Registry audit: shadcn not initialized, no third-party registries. Skipped.

## Files Audited
- frontend/src/app/globals.css, layout.tsx, page.tsx
- frontend/src/components/ChatDock.tsx, ConnectionStatus.tsx, Header.tsx, Panel.tsx, PriceCell.tsx, Sparkline.tsx, Terminal.tsx, Watchlist.tsx, WatchlistRow.tsx
- frontend/src/lib/format.ts, tickers.ts, usePriceStream.ts
- .planning/phases/01-live-price-terminal/01-UI-SPEC.md, 01-CONTEXT.md
