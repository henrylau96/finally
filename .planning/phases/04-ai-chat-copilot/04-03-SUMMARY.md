---
phase: 04-ai-chat-copilot
plan: 03
subsystem: frontend
tags: [chat, ui, e2e]
requires: [04-01, 04-02]
provides: [chat-dock-ui, useChat-hook, action-chips]
affects: [frontend/src/components/ChatDock.tsx, Terminal.tsx]
key-files:
  created:
    - frontend/src/lib/useChat.ts
    - frontend/src/components/ChatMessage.tsx
  modified:
    - frontend/src/components/ChatDock.tsx
    - frontend/src/components/Terminal.tsx
    - test/e2e/05-chat.spec.ts
decisions:
  - "Collapsed dock hides content with the hidden class rather than unmounting, so draft, messages and in-flight request survive"
  - "Chat messages rendered as React text nodes only; no markdown, no dangerouslySetInnerHTML"
metrics:
  tasks: 3
  completed: 2026-10-19
requirements: [UI-11, CHAT-01, CHAT-04, CHAT-05, CHAT-06]
---

# Phase 4 Plan 03: Chat dock UI Summary

The "FinAlly AI" dock now sends to /api/chat, shows a loading bubble, renders replies with green/red action chips, restores history on reload and refreshes portfolio and watchlist after actions.

## Tasks

1. RED (866a62f): added example-prompt, watchlist add/remove chip, failed-trade reason, reload history and pending-disabled tests. Against the placeholder dock, 5 failed (the original trade test plus the 4 new ones); the example-prompt test did not fail because it self-skips when no empty state exists.
2. GREEN (6f83ce8): `useChat` hook, `ChatMessage` with chips, rebuilt `ChatDock`, Terminal passes `onActions` calling `refresh()` and `load()`. Lint, typecheck, build clean; 01 then the executes/watchlist/server-reason/disabled tests passed (4/4).
3. Empty state (f7f02c1): `chat-empty` with three example buttons that fill but do not send. Fresh server, 01 then 03, 04, 05: 12/12 passed.

## Deviations from Plan

None. Note: the example-prompt test passes without exercising the click if the DB already has history; on a fresh DB after 01 it runs for real (the full run showed 12 passed, 0 skipped).

## Self-Check: PASSED
