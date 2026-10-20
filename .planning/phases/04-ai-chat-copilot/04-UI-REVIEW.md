# Phase 4 - UI Review

**Audited:** 2026-10-20
**Baseline:** 04-UI-SPEC.md (approved, including binding Checker Clarifications), inheriting 01/02/03-UI-SPEC.md
**Screenshots:** not captured (code-only audit; no Playwright MCP, no server started)

Out of scope by instruction: narrow/tablet layout (Phase 6, UI-13). Noted only: the dock is a fixed `w-[360px]` third grid column (`Terminal.tsx:36`, `ChatDock.tsx:58`), so below ~1100px the center column is squeezed. Not scored down.

---

## Pillar Scores

| Pillar | Score | Key Finding |
|--------|-------|-------------|
| 1. Copywriting | 4/4 | Every contract string, chip template, aria-label and error copy matches exactly |
| 2. Visuals | 3/4 | Dock header strip is 32px, not 24px, so its divider sits 8px below the Watchlist/Main chart title dividers |
| 3. Color | 3/4 | Chips and bubbles token-correct with `color-mix`; Phase 3 rgba literals (Heatmap fill, Sell hover, price flash) still not migrated |
| 4. Typography | 4/4 | Only 12/14 px and 400/600 in the dock; repo-wide still exactly 4 sizes, 2 weights |
| 5. Spacing | 3/4 | Bubbles, chips, list, input row, empty state all on-scale; header strip off by 8px |
| 6. Experience Design | 3/4 | Full state coverage (loading, empty, error, disabled, focus return, scroll); busy cursor on an empty-but-idle Send; loading bubble has no speakable text |

**Overall: 20/24** (Phase 3: 19/24)

---

## Top 3 Priority Fixes

1. **Dock header strip is 32px, contract says 24px (WARNING)** - `ChatDock.tsx:60` uses `px-2 py-1` around a `p-1` button holding a 16px SVG (`:69-71`): 4 + 4 + 16 + 4 + 4 = 32px. `Panel.tsx:21` titles are `py-1` + 16px line height = 24px. The chat header divider therefore sits 8px lower than the Watchlist and Main chart title dividers across the same row, breaking the terminal's aligned title band. Fix: `className="flex h-6 items-center px-2 ..."` (drop `py-1`), keep the button `p-1` so the 24px button fills the strip exactly.
2. **Color tokens still duplicated as rgba literals (WARNING)** - The spec's Color section states alpha tints are derived with `color-mix(in srgb, var(--color-X) N%, transparent)` "so tokens stay the single source (folds the Phase 3 review color finding)". Chips do this (`ChatMessage.tsx:24-25`), but `Heatmap.tsx:13` (`rgba(63,185,80,a)` / `rgba(248,81,73,a)`), `TradeBar.tsx:114` (`hover:bg-[rgba(117,57,145,0.2)]`) and `globals.css:52,57` (price flash) still hardcode the up/down/submit hues. Fix: `color-mix(in srgb, var(--color-up) ${Math.round(a*100)}%, transparent)` in `fill()`; `hover:bg-[color-mix(in_srgb,var(--color-submit)_20%,transparent)]`; `color-mix(in srgb, var(--color-up) 30%, transparent)` in the flash rules.
3. **Send shows a busy cursor when it is merely empty; loading bubble is silent to screen readers (WARNING)** - `ChatDock.tsx:142` applies `disabled:cursor-progress` for both disabled reasons (pending, and empty draft), so hovering Send on an idle empty dock shows a "working" cursor. The typing bubble (`ChatDock.tsx:11-15`) is `role="status"` with only `aria-label` and three empty spans; live regions announce text content, so "FinAlly is thinking" is typically never spoken. Fix: `pending ? "cursor-progress" : "disabled:cursor-not-allowed"` (or `cursor-default`) on Send; add `<span className="sr-only">FinAlly is thinking</span>` inside the loading bubble.

Further items below (Send hover brightens while disabled, focus return while collapsed, chip long-token overflow, selected heatmap cell hover overlap).

---

## Detailed Findings

### Pillar 1: Copywriting (4/4)
- Dock title "FinAlly AI" (`ChatDock.tsx:62`); placeholder "Ask FinAlly...", aria "Message FinAlly" (`:131-132`); Send visible "Send", aria "Send message" (`:140,144`); loading aria "FinAlly is thinking" (`:14`).
- Empty state heading and hint exact (`:89-91`); example prompts exactly "How is my portfolio doing?", "Buy 5 NVDA", "Add PYPL" per the binding clarification (`:7`).
- Chip templates exact (`ChatMessage.tsx:4-13`): "Bought/Sold {qty} {TICKER} @ {price}", "Added/Removed {TICKER}", "Failed: {side} {qty} {TICKER}. {reason}" with fallback "Could not complete the action.". Quantity uses `formatQty` (4 decimals trimmed), price `formatPrice`. Backend always returns `price` on OK trades (`backend/app/chat/execute.py:51`), so "@ --" cannot appear.
- Client failure copy "Could not reach FinAlly. Try again." exact (`useChat.ts:56`).
- `sr-only` speaker prefix "You said" / "FinAlly said" (`ChatMessage.tsx:48`). Timestamp `title` in `HH:mm:ss` via `en-GB`; backend stores UTC ISO with offset, so local time is correct.

### Pillar 2: Visuals (3/4)
- WARNING: header strip height 32px vs 24px contract (fix 1). The only structural deviation from the dock diagram.
- Bubbles flat (radius 0), 1px border, user right on `row-hover`, assistant left on `bg`, `max-w-[85%] min-w-0` (`ChatMessage.tsx:42-44`). Error stripe 2px `border-l-down` (`:45`). Typing bubble is an assistant-style bubble of three 4px dots (`ChatDock.tsx:15-22`).
- Focal point: the newest assistant bubble with chips (binding clarification) is achieved through auto-scroll to bottom and the green/red chip tint; no extra emphasis, which is acceptable.
- Collapsed: 48px rail with only the chevron, list and form `hidden` not unmounted (`:81,121`); title unmounted, which is harmless (static text). Chevron direction correct (">" collapses right, "<" expands).
- Heatmap fold-in landed: `role="button"`, `aria-pressed`, 2px inset primary ring on `data-selected` (`Heatmap.tsx:47-59`). Minor: the 1px muted hover outline also draws on the selected cell over the ring; consider `data-[selected=true]:hover:outline-none`.
- Needs human review (no screenshots): chip tint legibility (12% fill on `#0d1117`), dot pulse stagger visibility.

### Pillar 3: Color (3/4)
- Accent stays at two uses; dock title is muted, dock is not `active` (`ChatDock.tsx:62`). Purple only on Buy and Send (`:142`, `TradeBar.tsx:104`). `--color-down` in chat only on failed chips and the error stripe.
- Chips use `color-mix` 40% border / 12% fill on `--color-up`/`--color-down` (`ChatMessage.tsx:22-26`); verb text ("Bought", "Failed:") means color is never the only signal.
- Input `bg-bg` + border, placeholder `text-muted`; example buttons transparent with `hover:bg-row-hover` (`ChatDock.tsx:104,135`). All per table.
- WARNING: rgba literals remain in `Heatmap.tsx:13`, `TradeBar.tsx:114`, `globals.css:52,57` (fix 2). Fold-in item 4 was optional, but the Color section rule is stated generally and the Phase 3 finding is carried over unaddressed.
- Minor: Send `hover:brightness-110` still applies when disabled (`ChatDock.tsx:142`); add `disabled:hover:brightness-100` (same pattern exists on Buy).

### Pillar 4: Typography (4/4)
- Dock: title 12/600 uppercase tracking 0.05em; message text 14/400 sans; chips 12/400 mono tabular-nums with ticker not bolded; empty heading 14 muted, hint 12 muted; example buttons 12 sans; input 14 sans; Send 14/600. All match.
- Repo-wide distribution (components): `text-xs` 18, `text-sm` 17, `text-base` 3, `text-xl` 2; `font-semibold` 18, no other weights. Exactly the inherited 4 sizes and 2 weights. No arbitrary sizes.

### Pillar 5: Spacing (3/4)
- On-scale: bubble `p-2`, list `p-2 gap-2`, chip row `mt-2 gap-1`, chips `px-2 py-1`, input row `p-2 gap-1`, input/Send `h-8`, Send `w-16`, empty state `p-4 gap-4`, example buttons `h-8 px-2`, collapsed `w-12`. Exceptions (`w-[360px]`, 85%) are the declared ones.
- WARNING: header strip 32px vs 24px (fix 1).
- Minor: example buttons stack with `gap-1` (4px); contract does not specify, acceptable.

### Pillar 6: Experience Design (3/4)
- State coverage complete: optimistic user bubble, loading bubble removed (not hidden) on reply, inputs disabled with `aria-busy` (`ChatDock.tsx:119,128,141`), empty state hidden while pending, client error bubble not persisted, silent history failure, history merge that preserves messages sent before history loads (`useChat.ts:35`), double-send guard via `pendingRef`.
- Focus returns to the input after reply (`ChatDock.tsx:42-45`); Esc clears the draft (`:134`); Enter submits natively (real `type="submit"`). Example prompts fill and focus, never send.
- Auto-scroll on messages, pending and expand (`:37-40`), instant.
- Post-action refresh via `onActions` (`Terminal.tsx:49`). The network-error path also calls `onActions` (`useChat.ts:57`), a benign extra beyond the contract (keeps state truthful if the server executed before the connection dropped).
- Trade bar Enter-to-Buy and sticky selection fold-ins landed (`TradeBar.tsx:42-47`, `Terminal.tsx:24-32`), with E2E per 04-02-SUMMARY.
- WARNING: busy cursor on idle empty Send; loading status not spoken (fix 3).
- Minor: if the dock is collapsed while a request is pending, the post-reply `focus()` targets a hidden input and silently no-ops; on expand the user must click the input. Consider focusing on expand.
- Minor: chips are flex items with `break-words`; a long unbroken token in a server reason can still overflow because flex items default to `min-width: auto`. Add `min-w-0` or `[overflow-wrap:anywhere]` to the chip.
- No destructive confirmation by design (PLAN.md section 9); chips are the after-the-fact confirmation. Not a deduction.

---

## Registry Safety

Not applicable: no `components.json`, no shadcn or third-party registries, no new npm dependencies.

---

## Files Audited
- frontend/src/components/ChatDock.tsx
- frontend/src/components/ChatMessage.tsx
- frontend/src/components/Heatmap.tsx
- frontend/src/components/TradeBar.tsx
- frontend/src/components/Terminal.tsx
- frontend/src/components/Panel.tsx
- frontend/src/lib/useChat.ts
- frontend/src/lib/format.ts
- frontend/src/app/globals.css
- backend/app/chat/execute.py, backend/app/chat/store.py (action record and timestamp shape)
- .planning/phases/04-ai-chat-copilot/04-UI-SPEC.md, 04-CONTEXT.md, 04-0[1-5]-SUMMARY.md
- .planning/phases/03-trading-portfolio/03-UI-REVIEW.md
