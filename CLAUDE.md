# FinAlly Project - the Finance Ally

All project documentation is in the `planning` directory.

The key document is PLAN.md included in full below. The whole platform is being rebuilt from scratch via GSD (see `.planning/ROADMAP.md`); no backend or frontend code exists yet. The previous market data design is documented in `planning/MARKET_DATA_SUMMARY.md` with more details in the `planning/archive` folder, for reference only. Consult these docs only when required.

@planning/PLAN.md

<!-- GSD:project-start source:PROJECT.md -->
## Project

**FinAlly — AI Trading Workstation**

FinAlly (Finance Ally) is a single-user, AI-powered trading workstation that streams live market data, lets the user trade a simulated $10,000 portfolio, and includes an LLM chat assistant that analyzes positions and executes trades and watchlist changes on the user's behalf. It looks and feels like a modern Bloomberg terminal with an AI copilot, ships as one Docker container on port 8000, and is the capstone project of an agentic AI coding course, built entirely by coding agents.

**Core Value:** From one command, the user lands in a live, dark trading terminal where prices stream, trades fill instantly, and the AI copilot can trade for them through chat.

### Constraints

- **Tech stack**: FastAPI + uv (Python 3.14), Next.js TypeScript static export, Tailwind, SQLite, SSE, LiteLLM/OpenRouter/Cerebras — fixed by PLAN.md
- **Deployment**: single container, single port 8000, no CORS — students run one command
- **Tooling**: always `uv run` / `uv add`, never `python3` / `pip` — user rule
- **Code style**: simple, no over-engineering or defensive programming, short modules and functions, concise docstrings, no emojis, latest library APIs — user rule
- **Process**: work incrementally in small validated steps; identify and prove root cause before fixing — user rule
- **Visual**: dark theme (`#0d1117`/`#1a1a2e`, no pure black), accent yellow `#ecad0a`, blue `#209dd7`, purple `#753991` for submit buttons; ~500ms price flash
- **Testing**: E2E runs with `LLM_MOCK=true` so it needs no API key
<!-- GSD:project-end -->

<!-- GSD:stack-start source:STACK.md -->
## Technology Stack

Technology stack not yet documented. Will populate after codebase mapping or first phase.
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

Conventions not yet established. Will populate as patterns emerge during development.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

Architecture not yet mapped. Follow existing patterns found in the codebase.
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->
## Project Skills

| Skill | Description | Path |
|-------|-------------|------|
| cerebras-inference | Use this to write code to call an LLM using LiteLLM and OpenRouter with the Cerebras inference provider | `.claude/skills/cerebras/SKILL.md` |
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->

<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
