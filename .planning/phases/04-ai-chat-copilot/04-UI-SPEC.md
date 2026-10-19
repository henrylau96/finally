---
phase: 4
slug: ai-chat-copilot
status: approved
reviewed_at: 2026-10-19
shadcn_initialized: false
preset: none
created: 2026-10-19
---

# Phase 4 - UI Design Contract

> Extends the approved Phase 1, 2 and 3 contracts. All tokens, spacing, typography, color rules and the "Checker Clarifications" are inherited unchanged; this document only adds. Sources: 04-CONTEXT.md (locked), 03-UI-REVIEW.md (fold-in fixes), test/e2e/05-chat.spec.ts, helpers.ts, current ChatDock.tsx / TradeBar.tsx / Heatmap.tsx / Terminal.tsx. Autonomous choices are tagged (decision).

---

## Design System

| Property | Value |
|----------|-------|
| Tool | none (no `components.json`; shadcn gate: N per Phase 1, registry gate not applicable) |
| Preset | not applicable |
| Component library | none (React 19.3 + Tailwind 4.3 `@theme` tokens in `globals.css`) |
| Icon library | none (inline SVG chevron already in ChatDock; no new icons) |
| Font | Inherited: system sans for prose; monospace + tabular-nums for tickers, prices and chip text |

---

## Spacing Scale

Inherited scale (4, 8, 16, 24, 32, 48, 64). Phase 4 usage:

| Token | Value | Phase 4 usage |
|-------|-------|---------------|
| xs | 4px | Gap between chips; gap between typing dots; header button padding |
| sm | 8px | Bubble padding; gap between messages; input row padding; chip padding (horizontal 8px, vertical 4px); message list padding |
| md | 16px | Empty-state padding; gap between empty-state prompts group and text |
| lg | 24px | Dock header strip height |
| xl | 32px | Input and Send button height (matches trade bar controls); example prompt button min height |
| 2xl | 48px | Collapsed dock width (inherited `w-12`) |

Exceptions: dock width stays the inherited `w-[360px]`. Bubble max width is 85% of the list (percent, not a spacing token). Typing dots are 4px circles. No other off-scale values.

---

## Typography

Inherited: exactly 4 sizes (12 / 14 / 16 / 20), 2 weights (400, 600). No new sizes or weights. Body line height 1.5.

| Phase 4 element | Size | Weight | Notes |
|-----------------|------|--------|-------|
| Dock title "FinAlly AI" | 12px | 600 | uppercase, tracking 0.05em, muted (same style as other panel titles) |
| Message text (user and assistant) | 14px | 400 | sans, `whitespace-pre-wrap`, `break-words` (plain text, line breaks preserved) |
| Action chip text | 12px | 400 | mono, tabular-nums; ticker inside is not bolded |
| Empty-state heading | 14px | 400 | muted |
| Empty-state hint | 12px | 400 | muted |
| Example prompt buttons | 12px | 400 | sans, `--color-text` |
| Input text and placeholder | 14px | 400 | sans (prose, not mono) |
| Send label | 14px | 600 | |

---

## Color

Inherited split: 60% `--color-bg`, 30% `--color-surface` + `--color-border`, 10% accent. No new tokens or hues; alpha tints are derived with `color-mix(in srgb, var(--color-X) N%, transparent)` so tokens stay the single source (folds the Phase 3 review color finding).

| Element | Color |
|---------|-------|
| Dock shell | `--color-surface`, 1px `--color-border` (inherited) |
| Message list background | `--color-surface` (transparent over the shell) |
| User bubble | background `--color-row-hover`, 1px `--color-border`, text `--color-text`, right aligned |
| Assistant bubble | background `--color-bg`, 1px `--color-border`, text `--color-text`, left aligned |
| Error reply bubble | assistant bubble plus 2px left border `--color-down` (`data-error="true"`) |
| Action chip OK | text `--color-up`, 1px border `color-mix(--color-up 40%, transparent)`, fill `color-mix(--color-up 12%, transparent)` |
| Action chip failed | text `--color-down`, 1px border `color-mix(--color-down 40%, transparent)`, fill `color-mix(--color-down 12%, transparent)` |
| Typing bubble | assistant bubble; dots `--color-text-muted` |
| Input | background `--color-bg`, 1px `--color-border`, text `--color-text`, placeholder `--color-text-muted` |
| Send button | background `--color-submit` `#753991`, text `--color-text`, hover `filter: brightness(1.1)`, disabled opacity 0.5 (same as Buy) |
| Example prompt buttons | transparent, 1px `--color-border`, text `--color-text`; hover background `--color-row-hover` |
| Heatmap selected cell | 2px inset `--color-primary` ring (see fold-in fixes) |

Accent `#ecad0a` reserved for (unchanged): (1) "FinAlly" wordmark, (2) active panel title underline (Watchlist, Main chart). The chat dock title does NOT use accent and the dock is not an `active` panel (decision: keeps accent scarce). Purple `--color-submit` is used only for Buy, Send. Destructive/failure `--color-down` is used for failed chips, the error-reply stripe, the trade error and negative P&L only. Sign/verb text in every chip means color is never the only signal.

---

## Layout and Dock Structure

The dock stays the third column of the Phase 1 grid (`auto` width: 360px expanded, 48px collapsed), full height of the row, `min-h-0`, `flex flex-col`.

```
+---------------------------------+
| FINALLY AI                  [>] |  header strip 24px (px-2), border-b 1px
+---------------------------------+
| message list (flex-1, scroll)   |  role="log", aria-live="polite", p-2, gap-2
|   [assistant bubble]            |
|            [user bubble]        |
|   [ typing bubble ]             |
+---------------------------------+
| [ input (flex-1) ][ Send 64px ] |  row p-2, gap 4px, border-t 1px, controls 32px
+---------------------------------+
```

- Header: replaces the "Assistant" heading with `FinAlly AI`; toggle chevron button unchanged (`aria-expanded`, `aria-label` "Collapse chat panel" / "Expand chat panel"). Strip height 24px as other panel titles.
- Message list: `overflow-y-auto`, `flex flex-col gap-2 p-2`, `data-testid="chat-messages"`.
- Input row: `<form>` with `data-testid="chat-form"`; input `h-8 flex-1`, Send `h-8 w-16`; radius 0, flat terminal look (inherited).

### Collapsed behavior (decision)

- Width 48px (`w-12`), only the toggle button is shown (the title, list and input row are hidden with `hidden`, NOT unmounted), so message state, scroll position, a typed draft and an in-flight request survive collapse/expand.
- `chat-panel` stays in the DOM and visible in both states (`data-collapsed="true|false"` added). Default is expanded on load. State is not persisted across reloads (Phase 6 owns dock polish).
- If a reply arrives while collapsed, it is appended silently; on expand the list scrolls to the bottom. No unread badge (decision, out of scope).

---

## Message List

| Property | Contract |
|----------|----------|
| Element | `data-testid="chat-message"`, `data-role="user"` or `"assistant"`, `data-error="true"` only on error replies |
| Alignment | User: `self-end`, right. Assistant: `self-start`, left. Max width 85% of the list width; `min-w-0` |
| Bubble | padding 8px, 1px border, radius 0 (flat; no rounded chat bubbles to match the terminal look, decision) |
| Content | Plain text via React text node (no `dangerouslySetInnerHTML`, no markdown; decision, prevents injection and keeps the LLM output predictable). `whitespace-pre-wrap` preserves the model's line breaks |
| Timestamps | Not displayed (decision, density). `title` attribute on each bubble holds the local time from `created_at` (`HH:mm:ss`) |
| Role label | None visible; alignment and fill distinguish roles. Each bubble has `aria-label` "You said" / "FinAlly said" via a visually hidden prefix span (`sr-only`) so screen readers hear the speaker |
| Spacing | 8px between messages; chips sit 8px below the message text inside the same assistant bubble |
| Ordering | Oldest first; history (last 50 from `GET /api/chat/history`) loaded on mount, then appended live |
| History load failure | Silent: list shows the empty state (decision, consistent with P&L refetch rule) |

### Action chips (CHAT-04, CHAT-05, UI-11)

Rendered inside the assistant bubble beneath the text, in a wrapping flex row (`flex flex-wrap gap-1`, `mt-2`), one chip per action record, in execution order (watchlist first, then trades). Absent when `actions` is empty or null.

| Property | Contract |
|----------|----------|
| Element | `data-testid="chat-action"`, `data-ok="true"` or `"false"`, `data-type="trade"` or `"watchlist"` |
| Size | 12px mono, padding 4px 8px, 1px border, radius 0; may wrap to multiple lines (`break-words`), never truncated, so the failure reason is fully readable |
| Content contains | The ticker symbol always (E2E asserts `toContainText("AAPL")`) |

Chip copy (the price uses `formatPrice`; quantity uses the Phase 3 quantity format, up to 4 decimals trimmed):

| Case | Copy |
|------|------|
| Trade buy OK | "Bought 1 AAPL @ $190.02" |
| Trade sell OK | "Sold 2.5 TSLA @ $242.10" |
| Watchlist add OK | "Added PYPL" |
| Watchlist remove OK | "Removed PYPL" |
| Trade failed | "Failed: buy 10 AAPL. {server reason}" e.g. "Failed: buy 10 AAPL. Insufficient cash: need $1,900.20, have $812.00" |
| Watchlist failed | "Failed: add PYPL. {server reason}" |
| Failed, no reason in record | "Failed: buy 10 AAPL. Could not complete the action." |

Chips are not interactive (no hover, no focus, not buttons).

---

## Loading State (CHAT-09 UI, UI-11)

- `data-testid="chat-loading"` is an assistant-style bubble appended at the end of the list while the request is pending: three 4px dots (`--color-text-muted`) in a row, 4px gap, animated with the existing `status-pulse` keyframes (opacity 1 to 0.4, 1s) staggered 0 / 150ms / 300ms. `prefers-reduced-motion`: no animation, static dots (existing media rule covers `.status-pulse`).
- `role="status"` with `aria-label="FinAlly is thinking"`.
- Appears immediately on send (after the user bubble is appended optimistically); removed (not hidden) when the reply or an error arrives, so `toHaveCount(0)` passes.
- Input and Send are `disabled` and the form has `aria-busy="true"` while pending; cursor `progress` on disabled controls (same as the trade bar). The empty state is hidden while pending.

---

## Input Row

| Property | Contract |
|----------|----------|
| Input | `data-testid="chat-input"`, `type="text"`, `placeholder="Ask FinAlly..."`, `aria-label="Message FinAlly"`, `autocomplete="off"`, `maxLength=2000` (matches the server cap), 14px sans |
| Send | `data-testid="chat-send"`, `type="submit"`, visible label "Send", `aria-label="Send message"`, solid purple (see Color) |
| Enter | Native form submit: single text input plus a submit button, so Enter sends (the trade-bar Enter bug does not apply here because a real submit button exists) |
| Disabled rules | Send disabled while pending or when the trimmed input is empty. Input disabled while pending |
| Submit behavior | Trim; ignore empty. Append the user bubble immediately, clear the input, show `chat-loading`, POST `/api/chat {message}` |
| After reply | Append the assistant bubble, remove loading, re-enable, return focus to the input |
| Esc | Clears the draft (mirrors the trade bar) |
| Focus ring | Inherited 2px `--color-primary` |
| Tab order | Chat toggle, example prompts (when shown), input, Send (follows the trade bar and positions in the page order) |

---

## Empty State

Shown when there are zero messages and no pending request. `data-testid="chat-empty"`, centered in the list (`flex h-full flex-col items-center justify-center gap-4 p-4 text-center`).

| Element | Contract |
|---------|----------|
| Heading | 14px muted: "Ask FinAlly about your portfolio." |
| Hint | 12px muted: "It can analyze positions, place trades and manage your watchlist." |
| Example prompts | 3 buttons, `data-testid="chat-example"`, stacked, full width, 32px high, 1px border, left-aligned text 8px padding |
| Click behavior | Fills the input with the prompt text and focuses it. It does NOT auto-send (decision: user confirms with Enter/Send; avoids accidental trades) |

Prompts (chosen so each works in mock mode regexes `(buy|sell) <qty> <TICKER>` / `(add|remove) <TICKER>` or yields a plain mock reply):

1. "How is my portfolio doing?"
2. "Buy 5 NVDA"
3. "Add PYPL to my watchlist" - NOTE: mock regex is `(add|remove) <TICKER>`; the executor must make this text match (the regex must tolerate trailing words), or use "Add PYPL" instead. Decision: use exactly **"Add PYPL"** to be safe in mock mode.

Final prompt list: "How is my portfolio doing?", "Buy 5 NVDA", "Add PYPL".

---

## Error Replies

| Case | Behavior |
|------|----------|
| LLM failure or malformed output (server returns 200 with friendly text, no actions) | Rendered as a normal assistant bubble (no special styling; the server owns the copy, CHAT-07). No chips |
| Network failure, 5xx or non-JSON response | Client appends a local assistant bubble with `data-error="true"` (2px `--color-down` left border), copy: "Could not reach FinAlly. Try again." Not persisted. Input is re-enabled and keeps no draft (the user message stays in the list) |
| 422 (empty or oversized) | Cannot occur via UI (button disabled when empty, `maxLength=2000`); fall back to the network-failure copy |
| Chip failures | Never styled as bubble errors; they are failed chips (see above) because the assistant reply itself succeeded |

---

## Scrolling (decision)

- Auto-scroll to the bottom (`scrollTop = scrollHeight`) after: history load, a user message append, loading bubble appear, reply append, and dock expand.
- Always scroll on the user's own send. For an arriving reply scroll only if the user is within 48px of the bottom or the reply is the response to a just-sent message (which is always the case in single-shot replies), so simple rule: always scroll to bottom on any new message. No "new messages" pill (out of scope).
- `scroll-behavior` is instant (no smooth scrolling, avoids motion issues).

---

## Post-Action Refresh (UI-12)

When a reply contains at least one action with `ok: true`, the chat component calls an `onActions` callback from `Terminal` that (1) bumps the portfolio `refresh` so `usePortfolio` refetches portfolio and history (header cash/total, positions, heatmap, P&L), and (2) reloads the watchlist via `useWatchlist` load. Failed-only replies still refresh (cheap, keeps state truthful). No toast, no flash: the chips are the confirmation. Selection is unchanged by AI actions.

---

## Folded Phase 3 UI-Audit Fixes

1. **Enter submits Buy in the trade bar.** Add `onKeyDown` on BOTH the ticker and quantity inputs: if `e.key === "Enter"`, `preventDefault()` then `submit("buy")` (Esc handling on quantity stays). Buttons stay `type="button"`. The form `onSubmit` handler may remain as a harmless guard. Add an E2E: fill ticker and quantity, press Enter in quantity, expect a position and a lower cash.
2. **Selection stays after sell-out.** In `Terminal.tsx` the selection-validation effect must only assign a default when `selected` is empty (initial load). Drop the "must be in watchlist or positions" check: a sold-out or removed ticker keeps its chart and trade prefill. If the selected ticker is removed from the watchlist by the user, the selection also stays (chart still streams for held tickers; for non-held ones the empty-chart state from Phase 2 applies). The Phase 3 contract line "Sold-out: selection stays" is now honored.
3. **Heatmap selected style + semantics.** Cells get `role="button"` (was `img`) and `aria-pressed={selected}`; keep `aria-label`, `tabIndex=0`, Enter/Space handlers. Selected style: `box-shadow: inset 0 0 0 2px var(--color-primary)` via `data-[selected=true]:shadow-[inset_0_0_0_2px_var(--color-primary)]`. Hover outline (1px muted) stays for unselected cells; the focus-visible outline is unchanged and compatible. Update the Phase 3 heatmap Cell "Element" row accordingly (`role="button"`).
4. Optional low-risk review nits the executor may fold in while touching these files (not gating): heatmap `fill()` using `color-mix` on tokens instead of rgba literals; Sell hover using `color-mix(var(--color-submit) 20%, transparent)`.

---

## Copywriting Contract

| Element | Copy |
|---------|------|
| Dock title | "FinAlly AI" |
| Primary CTA | "Send" (solid purple) |
| Input placeholder / a11y | "Ask FinAlly..." / "Message FinAlly" |
| Send a11y | "Send message" |
| Empty state heading | "Ask FinAlly about your portfolio." |
| Empty state body | "It can analyze positions, place trades and manage your watchlist." |
| Example prompts | "How is my portfolio doing?" / "Buy 5 NVDA" / "Add PYPL" |
| Loading a11y | "FinAlly is thinking" |
| Chip: bought / sold | "Bought {qty} {TICKER} @ {price}" / "Sold {qty} {TICKER} @ {price}" |
| Chip: watchlist | "Added {TICKER}" / "Removed {TICKER}" |
| Chip: failure | "Failed: {side} {qty} {TICKER}. {server reason}" / "Failed: {add|remove} {TICKER}. {server reason}" |
| Error: client request failed | "Could not reach FinAlly. Try again." |
| Error: LLM failure (server-owned text) | Friendly assistant message from the backend, e.g. "Sorry, I couldn't process that. Please try again." (backend must keep it plain and actionable) |
| Destructive confirmation | None, by design. AI trades auto-execute with no dialog (PLAN.md section 9: simulated money, demo fluidity). Chips are the after-the-fact confirmation |

---

## Registry Safety

| Registry | Blocks Used | Safety Gate |
|----------|-------------|-------------|
| shadcn official | none (Tool: none) | not applicable |
| third-party | none | not applicable |

No new npm dependency (no markdown renderer, no icon library, no animation library).

---

## Test Hooks

| test id | Element | Notes |
|---------|---------|-------|
| `chat-panel` | dock `<aside>` | always in the DOM and visible; `data-collapsed` |
| `chat-messages` | scrolling list | `role="log"` |
| `chat-message` | one bubble | `data-role` user or assistant; `data-error="true"` on client-side error replies |
| `chat-action` | one chip | `data-ok` true or false, `data-type` trade or watchlist; text contains the ticker |
| `chat-loading` | typing bubble | present only while pending |
| `chat-input` | text input | `fill()` works; disabled while pending |
| `chat-send` | submit button | disabled while pending or empty |
| `chat-form` | input form | `aria-busy` while pending |
| `chat-empty` | empty state | only when there are no messages and not pending |
| `chat-example` | example prompt buttons (3) | click fills the input, does not send |
| `heatmap-cell-{TICKER}` | cell | now `role="button"`, `aria-pressed`, `data-selected` |

Existing E2E `05-chat.spec.ts` flow (fill, click Send, user bubble, assistant bubble containing "Mock response", `chat-action` with `data-ok="true"` containing AAPL, `chat-loading` count 0, cash falls) is satisfied by this contract.

---

## Decisions Log (autonomous)

1. Chat bubbles are flat (radius 0), user right/row-hover fill, assistant left/bg fill, both 1px border, max 85% width.
2. Plain text with preserved line breaks, no markdown, no `dangerouslySetInnerHTML`.
3. No visible timestamps; time in `title`; `sr-only` speaker prefix for accessibility.
4. Chips use up/down tokens with `color-mix` tints; failure chips carry the full server reason and wrap; verbs ("Bought", "Failed:") keep color from being the only signal.
5. Typing bubble is three pulsing 4px dots using the existing `status-pulse` keyframes; removed from the DOM on reply.
6. Send is a real `type="submit"` button so Enter works natively; trade bar gets explicit Enter key handling because it has no submit button.
7. Empty state offers 3 prompts that fill but do not send; texts chosen to match mock-mode regexes ("Buy 5 NVDA", "Add PYPL").
8. Client-side failures show a local, unpersisted error bubble with a 2px down-colored stripe; server-side LLM failures render as ordinary assistant text.
9. Collapsing hides but does not unmount the dock content, preserving history, draft and in-flight request; no unread badge.
10. Always auto-scroll to the bottom on any new message or expand; no smooth scroll.
11. Dock title does not use accent; accent stays at two uses.
12. Selection fix: default selection assigned only when empty; Heatmap cell semantics become `role="button"` + `aria-pressed` with a 2px inset primary ring.
13. No new colors, sizes, weights, spacing tokens or dependencies.

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

- **Example prompts (authoritative):** exactly "How is my portfolio doing?", "Buy 5 NVDA", "Add PYPL". Ignore any drafting note above about a different third prompt.
- **Dock focal point:** the newest assistant bubble with its action chips is the visual anchor of the chat dock.
- **Send label:** visible "Send" (accepted exception), `aria-label="Send message"`.
