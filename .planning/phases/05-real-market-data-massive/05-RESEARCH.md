# Phase 5: Real Market Data (Massive) - Research

**Researched:** 2026-10-20
**Domain:** Massive (ex-Polygon.io) REST polling behind the existing `MarketDataSource` interface
**Confidence:** HIGH (SDK source inspected directly at 2.9.0; prior build verified live)

## Summary

The `massive` SDK (PyPI 2.9.0, released 2026-10-16, Python >= 3.10, installs cleanly on 3.14) exposes the four methods this phase needs. All four are synchronous urllib3 calls, so they go through `asyncio.to_thread`. Any non-200 response raises `massive.exceptions.BadResponse(body_text)`, where `str(e)` is the raw JSON body. The only reliable way to spot a plan entitlement failure is to check `"NOT_AUTHORIZED" in str(e)`. The SDK does not expose the status code on the exception. Empty results (weekend or holiday grouped bars, an unknown ticker's prev close) come back as `[]`, not as an exception.

The prior build (`git show f2ef207^:backend/app/market/massive_client.py`) got the mode fallback, the NY-date logic and the `market_type="stocks"` string right. It had three defects this phase must fix. First, timestamps fell back to `time.time()` (it passed `None` for EOD and day/prev-day prices), so stale prices looked live. Second, `add_ticker` in snapshot mode fetched nothing. Third, the day change used the first price seen, not the previous close.

The biggest risk is not in the new module. The repo `.env` holds a real `MASSIVE_API_KEY`, and `app/main.py` calls `load_dotenv` and builds `source` at import time. Once the factory selects Massive, every existing test that runs the lifespan, and every smoke server, would call the real API. `conftest.py` must set `os.environ["MASSIVE_API_KEY"] = ""` before `from app import main`. `load_dotenv` defaults to `override=False`, so a present empty value wins.

**Primary recommendation:** Build one pure-parsing module and one source module. Inject the client into the source constructor so tests pass a tiny fake. Give `PriceCache.update` an optional `reference` close. Never pass `timestamp=None` from Massive code.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Client and modes
- Use the official `massive` Python SDK (`RESTClient(api_key=...)`), `uv add massive`. The SDK is synchronous: every call goes through `asyncio.to_thread`
- At `start`, try a snapshot (`get_snapshot_all("stocks", tickers=[...])`). On 403 `NOT_AUTHORIZED` switch to end-of-day (EOD) mode for the life of the source: grouped daily bars (`get_grouped_daily_aggs(date)`) using the New York date, stepping back a day while the date is today-before-close (403) or results are empty (weekend/holiday). See `planning/MASSIVE_API.md` sections 3.1, 3.3, 3.4, 4, 5
- Snapshot price preference per `planning/MASSIVE_API.md` section 4 (last trade if present, then minute bar close, day close, prev-day close); never assume `last_trade` exists
- Interval: `MASSIVE_POLL_INTERVAL` env in seconds; default 15 s in snapshot mode, 900 s in EOD mode (EOD ignores values below 900)
- A poll failure (network/API error) is logged and the loop continues on the next interval; it never kills the task
- Factory: `MASSIVE_API_KEY` set and non-empty (after strip) -> `MassiveDataSource`, else `SimulatorDataSource` (MKT-06)

#### New tickers and unknown tickers
- `add_ticker` fetches that one ticker immediately (single snapshot in snapshot mode, `get_previous_close_agg` in EOD mode) so it has a price at once (MKT-09); remove drops it from the tracked set and the cache
- Unknown/unpriced ticker: no cache entry, UI shows `--`; trading it hits the existing `TradeError("No price available for X")` -> 400

#### Timestamps and change
- The cache stores the real source timestamp (trade/bar time, ms -> seconds), never `time.time()` for Massive prices (MKT-09)
- Day change % uses the previous close when available (snapshot `prev_day.close`, EOD the prior bar's close or the bar open as fallback); `PriceCache.update` gains an optional session-open/reference argument; simulator behaviour unchanged

#### UI and health
- Header shows a small muted badge `EOD · as of <date>` when the newest price timestamp is older than 5 minutes; hidden for the simulator and fresh data
- `GET /api/health` returns `{"status": "ok", "source": "simulator"|"massive"}`

#### Testing
- Unit tests use a fake client object only (no network): mode fallback on NOT_AUTHORIZED, weekend step-back, price preference, timestamp conversion, add_ticker immediate fetch, poll error survival, factory selection
- Optional live smoke at the phase gate with the user's free key from `.env` (never print the key); not a gate requirement

### Claude's Discretion
- Module split (`massive_source.py` + small parsing helpers), exact log wording, badge styling within existing UI-SPEC tokens

### Deferred Ideas (OUT OF SCOPE)
- Massive WebSocket feeds (out of scope by PLAN.md)
- Phase 4 UI-audit fixes (dock header height, rgba tokens, Send cursor, sr-only loading text) fold into Phase 6
</user_constraints>

## Project Constraints (from CLAUDE.md)

- `uv add massive` / `uv run pytest`; never `pip` or `python3` directly
- Simple, short modules and functions, concise docstrings, no defensive programming, no emojis, latest APIs
- Work in small validated increments; prove root cause before fixing
- Single container / port 8000; verification servers on ports 8032+ with a scratch `DB_PATH`, stopped by recorded PID; never touch port 8000
- Visual tokens: muted text for the badge (existing `text-text-muted`), no new colours
- Never print `MASSIVE_API_KEY` / `OPENROUTER_API_KEY`

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| MKT-06 | Key set and non-empty -> Massive poller, else simulator | Factory with `os.environ.get("MASSIVE_API_KEY", "").strip()`; conftest blanks the key; health reports `source` |
| MKT-07 | Poll union of watched tickers on configurable interval; free tier grouped daily every 15 min; parse into simulator format | Verified signatures below; snapshot -> EOD fallback on `NOT_AUTHORIZED`; `max(interval, 900)` in EOD; writes `cache.update(ticker, price, timestamp, reference)` |
| MKT-09 | New ticker priced without waiting; true source timestamps | `add_ticker` fetches one ticker (no-op if already tracked); timestamp units table; `time.time()` never used for Massive; frontend badge from newest timestamp |
</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Source selection (MKT-06) | API / Backend (`market/factory.py`) | — | Env-driven, decided at import of `app.main` |
| Polling + mode fallback (MKT-07) | API / Backend (`market/massive_source.py`) | — | Background asyncio task, sync SDK in threads |
| Response parsing | API / Backend (`market/massive_parse.py`) | — | Pure functions over SDK models; easy unit tests |
| Price/timestamp/reference storage | In-memory cache (`market/cache.py`) | — | Single source of truth already feeding SSE |
| Source name for health | API / Backend (`api/health.py`) | — | `{"status","source"}` |
| Stale badge (MKT-09 UI) | Browser (`usePriceStream` + `Header`) | — | Timestamps already arrive per ticker over SSE |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| massive | 2.9.0 (PyPI, 2026-10-16) | Official Massive REST client | Locked decision; `[VERIFIED: PyPI JSON + SDK source inspected]` |

Deps pulled in: `certifi`, `urllib3>=1.26.9`, `websockets>=14.0` `[VERIFIED: PyPI requires_dist]`. Nothing else is needed: `zoneinfo` and `asyncio` are stdlib.

**Installation:**
```bash
cd backend && ~/.local/bin/uv add massive
```

## Package Legitimacy Audit

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| massive | PyPI | ~1 yr (first release 2025-10-20; Polygon client renamed) | not checked | github.com/massive-com/client-python | [OK] | Approved |

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Verified SDK API (massive 2.9.0)

Signatures come from `inspect.signature` and the method source, run in an isolated `uv run --no-project --with massive==2.9.0` environment `[VERIFIED: SDK source]`:

```python
RESTClient(api_key: str | None = None, connect_timeout=10.0, read_timeout=10.0, retries=3, base="https://api.massive.com", ...)
get_snapshot_all(market_type: str | SnapshotMarketType, tickers: str | list[str] | None = None, ..., include_otc=False) -> list[TickerSnapshot]
get_snapshot_ticker(market_type: str | SnapshotMarketType, ticker: str, ...) -> TickerSnapshot
get_grouped_daily_aggs(date: str | datetime.date, adjusted: bool | None = None, ..., locale="us", market_type="stocks") -> list[GroupedDailyAgg]
get_previous_close_agg(ticker: str, adjusted: bool | None = None, ...) -> list[PreviousCloseAgg]   # annotation says PreviousCloseAgg, but "results" is a JSON list, so it returns a list
```

Behaviour of `BaseClient._get`, read from the source:
- `resp.status != 200` -> `raise BadResponse(resp.data.decode("utf-8"))`. The message is the raw body, for example `{"status":"NOT_AUTHORIZED","request_id":"...","message":"You are not entitled to this data..."}`. There is no status-code attribute.
- If the result key is missing (`results` / `tickers` / `ticker`), the call returns `[]`. That happens for weekend grouped bars and for an unknown ticker's prev close.
- urllib3 `Retry(total=3, status_forcelist=[413,429,499,500,502,503,504], backoff_factor=0.1)`, so a 429 retries quickly, then raises.
- `RESTClient(api_key=None)` raises `AuthError` with no network call. A non-empty string never raises at construction, so building the client in the factory is safe offline.
- `market_type="stocks"` must be a plain string. The `SnapshotMarketType` enum is interpolated into the URL and 404s (`planning/MASSIVE_API.md` 3.1; prior build commit de82f7a).

**NOT_AUTHORIZED detection:**
```python
from massive.exceptions import BadResponse

def not_authorized(e: Exception) -> bool:
    """True for a plan-entitlement 403 (also today-before-close on grouped bars)."""
    return isinstance(e, BadResponse) and "NOT_AUTHORIZED" in str(e)
```

### Timestamps and fields (SDK attribute -> unit)

| Model | Price attr | Time attr | Unit | Notes |
|-------|-----------|-----------|------|-------|
| `TickerSnapshot.last_trade` (`LastTrade`) | `price` | `sip_timestamp` | ns | Present only on Developer+ plans; there is no `.timestamp` |
| `TickerSnapshot.min` (`MinuteSnapshot`) | `close` | `timestamp` | ms | Pre-market can be `close=0, timestamp=0` (verified via `from_dict`) |
| `TickerSnapshot.day` / `.prev_day` (`Agg`) | `close` | `timestamp` | ms | Snapshot `day`/`prevDay` carry **no `t`**, so `timestamp is None` |
| `TickerSnapshot` | — | `updated` | ns | Snapshot update time; may be absent |
| `GroupedDailyAgg` | `close`, `open`, `ticker` | `timestamp` | ms | Grouped bars for every US stock on that date |
| `PreviousCloseAgg` | `close`, `open`, `ticker` | `timestamp` | ms | One item list |

All price fields are `Optional`. Treat `None` and `0` the same way, with plain truthiness.

## Architecture Patterns

### System Architecture Diagram

```
 lifespan start
     |
     v
 factory: MASSIVE_API_KEY.strip() ? ----no----> SimulatorDataSource (unchanged)
     | yes
     v
 MassiveDataSource(cache, RESTClient(api_key), interval)
     |
 start(tickers) --> _poll_once() (awaited, so the cache has data before the snapshot recorder runs)
     |                 |
     |        mode == snapshot? --yes--> to_thread(get_snapshot_all("stocks", tickers))
     |                 |                    | BadResponse NOT_AUTHORIZED -> mode = eod, interval = max(i, 900), poll again
     |                 |                    v
     |                 |               snapshot_quote(snap) -> (price, ts_seconds, prev_close) or None
     |                 |
     |                 +--eod--> to_thread(latest_grouped_bars(client, ny_today))
     |                              date d = NY today; 403 NOT_AUTHORIZED or [] -> d -= 1 day (max 5 tries)
     |                              keep {ticker: bar} for all tickers; write only tracked ones
     v
 create_task(_loop): sleep(interval) -> _poll_once (errors logged, loop continues)
     |
 cache.update(ticker, price, timestamp=ts, reference=prev_close_or_open)
     |
 SSE price_events (version change) --> browser usePriceStream --> Header badge if newest ts < now - 300 s

 add_ticker(t): already tracked -> return | else track + fetch one
     snapshot: get_snapshot_ticker("stocks", t) ; eod: grouped bar if cached else get_previous_close_agg(t)
     failure/empty -> log, no cache entry (trade path then raises TradeError -> 400)
```

### Recommended Project Structure
```
backend/app/market/
├── massive_parse.py    # pure: snapshot_quote, bar_quote, latest_grouped_bars, not_authorized
├── massive_source.py   # MassiveDataSource (start/stop/add/remove/get_tickers, _poll_once, _loop)
├── cache.py            # update(..., reference: float | None = None)
├── factory.py          # env selection + poll interval parse
backend/tests/market/
├── test_massive_parse.py
├── test_massive_source.py
├── test_factory.py
```

### Pattern 1: Snapshot price preference with a real timestamp
```python
Quote = tuple[float, float, float | None]  # price, unix seconds, previous close

def snapshot_quote(snap: TickerSnapshot) -> Quote | None:
    """Best price with its source time; None when no price or no timestamp."""
    prev = snap.prev_day.close if snap.prev_day and snap.prev_day.close else None
    updated = snap.updated / 1e9 if snap.updated else None
    if snap.last_trade and snap.last_trade.price and snap.last_trade.sip_timestamp:
        return snap.last_trade.price, snap.last_trade.sip_timestamp / 1e9, prev
    if snap.min and snap.min.close and snap.min.timestamp:
        return snap.min.close, snap.min.timestamp / 1e3, prev
    price = (snap.day.close if snap.day and snap.day.close else None) or prev
    return (price, updated, prev) if price and updated else None
```
The last branch uses `updated` because snapshot `day`/`prevDay` carry no time. If there is no timestamp at all, skip the ticker rather than invent one.

### Pattern 2: EOD grouped bars by New York date
```python
NY = ZoneInfo("America/New_York")

def latest_grouped_bars(client, today: date, tries: int = 5) -> dict[str, GroupedDailyAgg]:
    """Bars for the newest NY trading day the plan may read, stepping back over 403/empty days."""
    day = today
    for _ in range(tries):
        try:
            bars = client.get_grouped_daily_aggs(day.isoformat(), adjusted=True)
        except BadResponse as e:
            if not not_authorized(e):
                raise
            bars = []
        if bars:
            return {b.ticker: b for b in bars if b.close}
        day -= timedelta(days=1)
    return {}
```
The caller passes `datetime.now(NY).date()`, so tests can pass a fixed date with no clock patching. Turn a bar into a quote with `(bar.close, bar.timestamp / 1e3, bar.open)`. The open is the reference fallback (see Open Question 1).

### Pattern 3: Source with injected client
```python
class MassiveDataSource(MarketDataSource):
    name = "massive"

    def __init__(self, cache: PriceCache, client, interval: float = 15.0) -> None:
        self._cache, self._client, self._interval = cache, client, interval
        self._mode = "snapshot"
        self._tickers: list[str] = []
        self._bars: dict[str, GroupedDailyAgg] = {}
        self._task: asyncio.Task | None = None
```
The factory builds `RESTClient(api_key=key)`. Tests pass a fake class with the four methods and a call log. Use `name = "simulator"` on `SimulatorDataSource` too, and health reads `source.name` (via `create_health_router(source)`, or a `request.app.state.source` set in the lifespan).

### Pattern 4: Cache reference close
```python
def update(self, ticker, price, timestamp=None, reference=None) -> PriceUpdate:
    ...
    if reference is not None:
        self._opens[ticker] = round(reference, 2)
    open_price = self._opens.setdefault(ticker, price)
```
Overwrite rather than `setdefault` when a reference is given, so a new trading day moves the reference. The simulator never passes `reference`, so its behaviour stays the same.

### Pattern 5: Stale badge without impure render
`eslint-plugin-react-hooks` 7.1.1 (installed) ships the `react-hooks/purity` rule, which flags `Date.now()` during render `[VERIFIED: node_modules grep]`. So compute staleness in the `onmessage` handler inside `usePriceStream`:
```ts
const newest = Math.max(...Object.values(next).map((q) => q.timestamp));
setAsOf(Date.now() / 1000 - newest > 300 ? newest : null);
```
`Header` receives `asOf?: number | null` and renders `EOD · as of {date}` with `text-text-muted text-xs`. Format the date with `toLocaleDateString("en-US", { timeZone: "America/New_York", ... })`, so a browser west of New York does not show the previous day for a midnight-ET bar timestamp.

### Anti-Patterns to Avoid
- **`timestamp=None` from Massive code:** the cache silently substitutes `time.time()`, which was the prior build's main bug.
- **Fetching in `add_ticker` for an already-tracked ticker:** `reconcile_stream` calls `source.add_ticker` after every trade for held tickers, so each trade would cost an API call. On the free tier (5/min) that quickly causes 429s. Return early.
- **`SnapshotMarketType.STOCKS`:** produces a 404 URL. Use `"stocks"`.
- **Building the source with the real `.env` key in tests:** see Pitfall 1.
- **Parsing `BadResponse` JSON to read a status:** the substring check is enough. Do not build an error-class hierarchy.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| HTTP, auth header, retries, JSON -> models | httpx calls to `api.massive.com` | `massive.RESTClient` | Locked; retries and model mapping already done |
| NY trading date | UTC offset math | `zoneinfo.ZoneInfo("America/New_York")` | DST-correct |
| Market holiday calendar | holiday tables | step back on empty/403, max 5 tries | The API is the calendar |
| Test doubles of SDK models | dicts / MagicMock attributes | `TickerSnapshot.from_dict({...})`, `GroupedDailyAgg.from_dict({...})` | Real field mapping (`T`, `c`, `t`, `lastTrade.p`) catches attribute-name bugs |

## Common Pitfalls

### Pitfall 1: Real key leaks into the test suite and smoke servers
**What goes wrong:** `.env` has a non-empty `MASSIVE_API_KEY` (verified present; value not printed). `app/main.py` runs `load_dotenv(...)` and then `source = create_market_data_source(cache)` at import. Every `client` fixture lifespan would start a real Massive poller.
**How to avoid:** at the top of `backend/tests/conftest.py`, before `from app import main`, add `os.environ["MASSIVE_API_KEY"] = ""`. python-dotenv `set_as_environment_variables` skips keys already in `os.environ` when `override=False` `[VERIFIED: dotenv source]`. Simulator smoke servers must also be started with `MASSIVE_API_KEY=` in their environment. `test/docker-compose.test.yml` already sets `MASSIVE_API_KEY: ""`.
**Warning signs:** slow tests, `massive` log lines in pytest output, a health test returning `source: massive`.

### Pitfall 2: Free-tier rate limit (5 calls/min)
**What goes wrong:** startup on a Monday costs snapshot 403 + today 403 + Sun + Sat + Fri, which is 5 calls. Adding tickers right afterwards can hit 429. The SDK retries 3 times with a ~0.1-0.4 s backoff and then raises `BadResponse`.
**How to avoid:** in EOD `add_ticker`, use the cached grouped bar (it covers all ~10k US tickers) and call `get_previous_close_agg` only when the ticker is missing. Make `add_ticker` a no-op for tracked tickers. Log and continue on failure.

### Pitfall 3: Today-before-close 403 on grouped bars
**What goes wrong:** the free tier rejects the current NY date with `NOT_AUTHORIZED` ("Attempted to request today's data before end of day"). The prior build avoided this by starting at yesterday, which then missed today's bar after the close.
**How to avoid:** start at NY today, and treat both NOT_AUTHORIZED and `[]` as "step back" inside `latest_grouped_bars` only. Any other `BadResponse` propagates to the poll's log-and-continue handler.

### Pitfall 4: Mode switch must happen once, not loop
**What goes wrong:** if the EOD path also raises NOT_AUTHORIZED, a naive "on 403 switch mode and retry" recursion can loop.
**How to avoid:** the snapshot -> EOD switch applies only when `self._mode == "snapshot"`. After switching, call the EOD fetch once directly, with no recursion.

### Pitfall 5: `add_ticker` holds the trade lock during network I/O
**What goes wrong:** `services.place_trade` and `add_to_watchlist` call `source.add_ticker` under `app.state.trade_lock`. A slow request (10 s connect + 10 s read, plus retries) blocks other trades for that long.
**How to avoid:** accept it, since this is single-user and the call is a single small request. Always use `asyncio.to_thread` so the event loop and SSE keep running. Do not add extra timeouts or caching layers.

### Pitfall 6: Badge date in the wrong timezone
**What goes wrong:** a bar `timestamp` near NY midnight, rendered in local time west of NY, shows the prior date.
**How to avoid:** format with `timeZone: "America/New_York"`.

### Pitfall 7: `react-hooks/purity` lint failure
**What goes wrong:** `Date.now()` in a component body fails `npm run lint`.
**How to avoid:** compute it in the SSE event handler (Pattern 5).

### Pitfall 8: Existing exact-match health test
`backend/tests/test_health.py` asserts `== {"status": "ok"}`. Update it to `{"status": "ok", "source": "simulator"}`. This depends on Pitfall 1's conftest blanking.

## Code Examples

### Fake client for tests
```python
from massive.exceptions import BadResponse
from massive.rest.models import GroupedDailyAgg, PreviousCloseAgg, TickerSnapshot

NOT_AUTH = '{"status":"NOT_AUTHORIZED","message":"You are not entitled to this data."}'

class FakeClient:
    """Records calls; each attribute is a value or an exception to raise."""
    def __init__(self, snapshots=None, grouped=None, single=None, prev=None):
        self.snapshots, self.grouped, self.single, self.prev = snapshots, grouped or {}, single, prev
        self.calls: list[tuple] = []

    def _ret(self, value):
        if isinstance(value, Exception):
            raise value
        return value

    def get_snapshot_all(self, market_type, tickers=None):
        self.calls.append(("all", market_type, tuple(tickers)))
        return self._ret(self.snapshots)

    def get_snapshot_ticker(self, market_type, ticker):
        self.calls.append(("one", ticker))
        return self._ret(self.single)

    def get_grouped_daily_aggs(self, date, adjusted=None):
        self.calls.append(("grouped", date))
        return self._ret(self.grouped.get(date, []))

    def get_previous_close_agg(self, ticker, adjusted=None):
        self.calls.append(("prev", ticker))
        return self._ret(self.prev or [])
```
Build models with `GroupedDailyAgg.from_dict({"T": "AAPL", "o": 188.0, "c": 190.2, "t": 1760731200000})` and `TickerSnapshot.from_dict({"ticker": "AAPL", "lastTrade": {"p": 190.5, "t": 1760790000_000000000}, "prevDay": {"c": 188.0}})`.

### Factory
```python
def create_market_data_source(cache: PriceCache) -> MarketDataSource:
    """Massive when MASSIVE_API_KEY is non-empty, else the simulator."""
    key = os.environ.get("MASSIVE_API_KEY", "").strip()
    if not key:
        return SimulatorDataSource(cache)
    interval = float(os.environ.get("MASSIVE_POLL_INTERVAL", "").strip() or 15)
    return MassiveDataSource(cache, RESTClient(api_key=key), interval)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `polygon-api-client`, `api.polygon.io` | `massive`, `api.massive.com` (legacy host still works) | 2025-10 rename | Use `from massive import RESTClient` |
| Prior build: `None` timestamps -> `time.time()` | Source timestamps only | This phase | Stale EOD visible as such |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Snapshot `updated` (ns) is present when `day`/`prev_day` are the only prices | Pattern 1 | Pre-market tickers are skipped (`--`) on Starter until the first minute bar; low impact, and paid plans only |
| A2 | Free-tier grouped bar for NY "today" becomes available after the close the same evening | Pitfall 3 | Only extra step-back calls; behaviour still correct |
| A3 | 403 body for snapshots contains the literal `NOT_AUTHORIZED` | NOT_AUTHORIZED detection | Verified live by the prior build (commit de82f7a) and in MASSIVE_API.md; low risk |

## Open Questions (RESOLVED)

1. **EOD reference close: the prior bar's close vs the bar's open**
   - What we know: the grouped endpoint returns one day, so the prior close needs a second grouped call (one more of the 5/min).
   - RESOLVED: use `bar.open` as the EOD reference, which CONTEXT allows as the fallback. Snapshot mode uses `prev_day.close`. This keeps startup within the rate limit.
2. **EOD `add_ticker`: grouped-bar lookup before `get_previous_close_agg`**
   - RESOLVED: look in `self._bars` first (zero calls), then fall back to prev close. This stays within the locked decision and avoids 429s (Pitfall 2).

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| uv | install/tests | yes | `~/.local/bin/uv` | — |
| Python | backend | yes | 3.14.4 | — |
| massive (PyPI) | MKT-07 | resolvable | 2.9.0 | — |
| Massive API key | optional live smoke | yes (free tier, in `.env`) | — | Skip smoke; unit tests cover everything |
| Node/npm (Windows wrappers) | frontend lint/build | yes | — | — |

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.1 + pytest-asyncio (auto mode); eslint 9 + tsc + next build |
| Config file | `backend/pyproject.toml` |
| Quick run command | `cd backend && ~/.local/bin/uv run pytest tests/market -q` |
| Full suite command | `cd backend && ~/.local/bin/uv run pytest -q && cd ../frontend && npm run lint && npm run typecheck && npm run build` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| MKT-06 | key non-empty -> `MassiveDataSource`; empty / whitespace / unset -> simulator; interval parsed | unit | `uv run pytest tests/market/test_factory.py -q` | ❌ W0 |
| MKT-06 | health returns `source: simulator` in tests | integration | `uv run pytest tests/test_health.py -q` | ✅ (update) |
| MKT-07 | price preference last_trade > min > day > prev_day; zero/None skipped | unit | `uv run pytest tests/market/test_massive_parse.py -k quote -q` | ❌ W0 |
| MKT-07 | grouped step-back over 403-today and empty weekend days; gives up after 5; other BadResponse raises | unit | `uv run pytest tests/market/test_massive_parse.py -k grouped -q` | ❌ W0 |
| MKT-07 | NOT_AUTHORIZED on snapshot -> EOD mode, interval >= 900, only tracked tickers cached; `"stocks"` string passed | unit | `uv run pytest tests/market/test_massive_source.py -k "fallback or eod" -q` | ❌ W0 |
| MKT-07 | poll exception logged, loop keeps running (fast interval, second poll happens) | unit | `uv run pytest tests/market/test_massive_source.py -k survives -q` | ❌ W0 |
| MKT-07 | `reference` sets day change from prev close; simulator path unchanged | unit | `uv run pytest tests/market/test_cache.py -q` | ✅ (extend) |
| MKT-09 | timestamps ns/ms -> seconds; cache timestamp equals source time, never now | unit | `uv run pytest tests/market/test_massive_parse.py tests/market/test_massive_source.py -k timestamp -q` | ❌ W0 |
| MKT-09 | `add_ticker` fetches one ticker at once (snapshot: `get_snapshot_ticker`; EOD: cached bar or prev close); no call when already tracked; failure leaves no cache entry | unit | `uv run pytest tests/market/test_massive_source.py -k add_ticker -q` | ❌ W0 |
| MKT-09 | stale badge renders only for old timestamps | static + manual | `cd frontend && npm run lint && npm run typecheck && npm run build` | ✅ |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/market -q` (backend) or lint + typecheck (frontend)
- **Per wave merge:** full suite command
- **Phase gate:** full suite green, plus the Playwright regression on a simulator server (`MASSIVE_API_KEY=` explicitly), plus an optional live EOD smoke

### Wave 0 Gaps
- [ ] `backend/tests/conftest.py`: `os.environ["MASSIVE_API_KEY"] = ""` before `from app import main`
- [ ] `backend/tests/market/test_massive_parse.py`, `test_massive_source.py`, `test_factory.py` (FakeClient helper inside the source test module, or in conftest)
- [ ] `uv add massive`

## Security Domain

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | — |
| V5 Input Validation | yes | Tickers already validated (1-5 letters, uppercase) by `api/schemas.py` before reaching the source |
| V7 Error/Logging | yes | Log `str(e)` of `BadResponse` (it is the response body, which contains no key). Never log the client or headers; the SDK only redacts the key in `trace` mode |
| V6 Cryptography | no | TLS handled by the SDK (certifi, CERT_REQUIRED) |

| Pattern | STRIDE | Mitigation |
|---------|--------|-----------|
| API key disclosure in logs/output | Information disclosure | Never print env or client headers; smoke checks `/api/health` source only |
| Rate-limit exhaustion via repeated add_ticker | Denial of service | No-op for tracked tickers; reuse grouped bars |

## Sources

### Primary (HIGH)
- `massive` 2.9.0 SDK source (`RESTClient` methods, `BaseClient._get`, `exceptions`, models), inspected via `uv run --no-project --with massive==2.9.0`
- PyPI JSON `pypi.org/pypi/massive/json`: version, release date, requires_dist, repo URL
- `planning/MASSIVE_API.md`: live-verified error bodies, plan matrix, grouped 403 behaviour
- Prior build `git show f2ef207^:backend/app/market/massive_client.py`, `tests/market/test_massive.py`, commits de82f7a / a92a2ef
- python-dotenv `DotEnv.set_as_environment_variables` source (override semantics)
- `frontend/node_modules/eslint-plugin-react-hooks` 7.1.1 (`purity` rule lists `Date.now`)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH (SDK inspected at the exact version)
- Architecture: HIGH (fits existing interface; prior build proved the modes live)
- Pitfalls: HIGH for 1, 3, 4, 7 and 8 (verified in code); MEDIUM for 2 (rate-limit arithmetic)

**Research date:** 2026-10-20
**Valid until:** 2026-11-20
