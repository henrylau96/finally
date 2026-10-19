# Phase 5: Real Market Data (Massive) - Context

**Gathered:** 2026-10-20
**Status:** Ready for planning

<domain>
## Phase Boundary

A user with a `MASSIVE_API_KEY` gets real market data through the same pipeline as the simulator. Delivers: a `MassiveDataSource` implementing `MarketDataSource`, factory selection by env var, immediate prices for newly added tickers, true source timestamps, and a small stale-data indicator. Requirements: MKT-06, MKT-07, MKT-09.

Not in this phase: Docker, tablet layout, frontend unit tests, E2E compose (Phase 6).

</domain>

<decisions>
## Implementation Decisions

### Client and modes
- Use the official `massive` Python SDK (`RESTClient(api_key=...)`), `uv add massive`. The SDK is synchronous: every call goes through `asyncio.to_thread`
- At `start`, try a snapshot (`get_snapshot_all("stocks", tickers=[...])`). On 403 `NOT_AUTHORIZED` switch to end-of-day (EOD) mode for the life of the source: grouped daily bars (`get_grouped_daily_aggs(date)`) using the New York date, stepping back a day while the date is today-before-close (403) or results are empty (weekend/holiday). See `planning/MASSIVE_API.md` sections 3.1, 3.3, 3.4, 4, 5
- Snapshot price preference per `planning/MASSIVE_API.md` section 4 (last trade if present, then minute bar close, day close, prev-day close); never assume `last_trade` exists
- Interval: `MASSIVE_POLL_INTERVAL` env in seconds; default 15 s in snapshot mode, 900 s in EOD mode (EOD ignores values below 900)
- A poll failure (network/API error) is logged and the loop continues on the next interval; it never kills the task
- Factory: `MASSIVE_API_KEY` set and non-empty (after strip) -> `MassiveDataSource`, else `SimulatorDataSource` (MKT-06)

### New tickers and unknown tickers
- `add_ticker` fetches that one ticker immediately (single snapshot in snapshot mode, `get_previous_close_agg` in EOD mode) so it has a price at once (MKT-09); remove drops it from the tracked set and the cache
- Unknown/unpriced ticker: no cache entry, UI shows `--`; trading it hits the existing `TradeError("No price available for X")` -> 400

### Timestamps and change
- The cache stores the real source timestamp (trade/bar time, ms -> seconds), never `time.time()` for Massive prices (MKT-09)
- Day change % uses the previous close when available (snapshot `prev_day.close`, EOD the prior bar's close or the bar open as fallback); `PriceCache.update` gains an optional session-open/reference argument; simulator behaviour unchanged

### UI and health
- Header shows a small muted badge `EOD · as of <date>` when the newest price timestamp is older than 5 minutes; hidden for the simulator and fresh data
- `GET /api/health` returns `{"status": "ok", "source": "simulator"|"massive"}`

### Testing
- Unit tests use a fake client object only (no network): mode fallback on NOT_AUTHORIZED, weekend step-back, price preference, timestamp conversion, add_ticker immediate fetch, poll error survival, factory selection
- Optional live smoke at the phase gate with the user's free key from `.env` (never print the key); not a gate requirement

### Claude's Discretion
- Module split (`massive_source.py` + small parsing helpers), exact log wording, badge styling within existing UI-SPEC tokens

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backend/app/market/interface.py` (`MarketDataSource` ABC), `cache.py` (`PriceCache.update(ticker, price, timestamp)`), `models.py` (`PriceUpdate`, `day_change_pct` from `session_open`), `factory.py` (simulator only today), `simulator_source.py` (start/stop/add/remove pattern)
- `backend/app/services.py` already raises `TradeError("No price available for X")` when a trade ticker has no price after `add_ticker`
- `.env.example` already has `MASSIVE_API_KEY` and `MASSIVE_POLL_INTERVAL`
- Frontend `Header.tsx`, `usePriceStream` (has per-ticker timestamps)

### Established Patterns
- Background tasks started in the lifespan and cancelled on shutdown; sync I/O via `asyncio.to_thread`
- Verification on ports 8032+ with scratch DB_PATH; stop by recorded PID; never touch port 8000

### Integration Points
- `backend/app/main.py` lifespan uses `create_market_data_source(cache)`
- Prior build had `massive_client.py` (in git history before `f2ef207`) for reference only

</code_context>

<specifics>
## Specific Ideas

- Prior-build pitfalls: snapshot prices with missing timestamps looked live; adding a ticker on Massive gave it no starting price until the next poll
- The user's key is free tier: snapshots return NOT_AUTHORIZED, so the live smoke exercises EOD mode

</specifics>

<deferred>
## Deferred Ideas

- Massive WebSocket feeds (out of scope by PLAN.md)
- Phase 4 UI-audit fixes (dock header height, rgba tokens, Send cursor, sr-only loading text) fold into Phase 6

</deferred>
