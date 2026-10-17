# Massive API Reference (formerly Polygon.io)

Reference for fetching real-time and end-of-day (EOD) US stock prices for multiple tickers from Massive. Researched October 2026 against the official docs (`massive.com/docs`) and the `massive` Python SDK source (`github.com/massive-com/client-python`).

## 1. Overview

| Item | Value |
|---|---|
| Base URL | `https://api.massive.com` (legacy `https://api.polygon.io` still works) |
| Python SDK | `massive` on PyPI (latest 2.9.0, Python >= 3.10). Add it with `uv add massive` |
| Auth | `apiKey` query param, or `Authorization: Bearer <key>` header |
| SDK auth | `RESTClient(api_key=...)`. Defaults to `os.getenv("MASSIVE_API_KEY")` |
| Errors | HTTP != 200. SDK raises `massive.exceptions.BadResponse(body)` |
| SDK retries | 3 retries on 413, 429, 499, 500, 502, 503, 504 (urllib3 backoff) |
| SDK timeouts | 10s connect, 10s read |

Error body shape (unauthenticated example, verified live):

```json
{"status": "ERROR", "request_id": "a1178a75...", "error": "API Key was not provided"}
```

A valid key calling an endpoint its plan does not include gets `403` with `"status": "NOT_AUTHORIZED"`.

## 2. Plans and what they allow (Stocks)

This determines which endpoints FinAlly can use.

| Plan | Price | Calls/min | Recency | Snapshots | Trades (`lastTrade`) | WebSockets |
|---|---|---|---|---|---|---|
| Basic (free) | $0 | 5 | **End of day** | No | No | No |
| Starter | $29/mo | Unlimited | 15-min delayed | Yes | No | Yes |
| Developer | $79/mo | Unlimited | 15-min delayed | Yes | Yes | Yes |
| Advanced | $199/mo | Unlimited | Real-time | Yes | Yes | Yes |

What this means for FinAlly:

- **Free tier gets no snapshots.** The only option is EOD aggregates: the grouped daily bars for every ticker in one call, or the previous close one ticker at a time.
- **Starter/Developer snapshots** return `day`, `min` and `prevDay` bars. `lastTrade` is **only present if the plan includes trades** (Developer+). Code must not assume `lastTrade` exists.
- **Advanced** gives real-time snapshots with `lastTrade`.
- Snapshot data is cleared daily at 3:30 AM ET and fills again from about 4:00 AM ET. Early in the day, `day` values can be zero.

## 3. Endpoints for multi-ticker prices

### 3.1 Full Market Snapshot (best for live prices, Starter+)

`GET /v2/snapshot/locale/us/markets/stocks/tickers?tickers=AAPL,MSFT,TSLA`

One call returns every requested ticker. This is the main polling endpoint.

| Query param | Notes |
|---|---|
| `tickers` | Comma-separated and case-sensitive. Leave it out to get the whole market (about 10k tickers, so avoid that) |
| `include_otc` | Default `false` |

Response (abridged; single-ticker sample from the docs):

```json
{
  "status": "OK",
  "count": 1,
  "tickers": [{
    "ticker": "AAPL",
    "todaysChange": 0.98,
    "todaysChangePerc": 0.82,
    "updated": 1605195918306274000,
    "day":     {"o": 119.62, "h": 120.53, "l": 118.81, "c": 120.4229, "v": 28727868, "vw": 119.725},
    "prevDay": {"o": 117.19, "h": 119.63, "l": 116.44, "c": 119.49,  "v": 110597265, "vw": 118.4998},
    "min":     {"o": 120.435, "h": 120.468, "l": 120.37, "c": 120.4201, "v": 270796, "av": 28724441, "n": 762, "t": 1684428720000},
    "lastTrade": {"p": 120.47, "s": 236, "t": 1605195918306274000, "x": 10, "i": "4046", "c": [14, 41]},
    "lastQuote": {"p": 120.46, "s": 8, "P": 120.47, "S": 4, "t": 1605195918507251700}
  }]
}
```

**Timestamp units differ by field**:

| JSON field | SDK attribute | Unit |
|---|---|---|
| `updated` | `snap.updated` | nanoseconds |
| `lastTrade.t` | `snap.last_trade.sip_timestamp` | nanoseconds |
| `lastQuote.t` | `snap.last_quote.sip_timestamp` | nanoseconds |
| `min.t` | `snap.min.timestamp` | milliseconds |

SDK mapping (`massive.rest.models.TickerSnapshot`):

| JSON | SDK attribute | Type |
|---|---|---|
| `ticker` | `ticker` | `str` |
| `day` | `day` | `Agg` or `None` (`open, high, low, close, volume, vwap, timestamp`) |
| `prevDay` | `prev_day` | `Agg` or `None` |
| `min` | `min` | `MinuteSnapshot` or `None` (`open, high, low, close, volume, accumulated_volume, vwap, timestamp, transactions`) |
| `lastTrade` | `last_trade` | `LastTrade` or `None` (`price, size, sip_timestamp, participant_timestamp, exchange, conditions, id`) |
| `lastQuote` | `last_quote` | `LastQuote` or `None` |
| `todaysChange` | `todays_change` | `float` |
| `todaysChangePerc` | `todays_change_percent` | `float` |
| `updated` | `updated` | `int` (ns) |

Note: `LastTrade` has **no `timestamp` attribute**. Use `sip_timestamp` (ns).

```python
from massive import RESTClient
from massive.rest.models import SnapshotMarketType

client = RESTClient()  # reads MASSIVE_API_KEY

snapshots = client.get_snapshot_all(
    market_type=SnapshotMarketType.STOCKS,
    tickers=["AAPL", "MSFT", "TSLA"],
)
for snap in snapshots:
    if snap.last_trade:  # Developer+ plans
        price, ts = snap.last_trade.price, snap.last_trade.sip_timestamp / 1e9
    elif snap.min and snap.min.close:  # Starter: latest minute bar
        price, ts = snap.min.close, snap.min.timestamp / 1e3
    else:  # pre-market, nothing traded yet today
        price, ts = snap.prev_day.close, None
    print(snap.ticker, price, ts, snap.todays_change_percent)
```

### 3.2 Single Ticker Snapshot (Starter+)

`GET /v2/snapshot/locale/us/markets/stocks/tickers/{ticker}` returns the same object as above under a `"ticker"` key.

```python
snap = client.get_snapshot_ticker(SnapshotMarketType.STOCKS, "AAPL")
```

Use this only for one-off lookups, such as checking that a ticker is valid before adding it to the watchlist. Use 3.1 for polling.

### 3.3 Grouped Daily Bars: EOD for all tickers in one call (all plans)

`GET /v2/aggs/grouped/locale/us/market/stocks/{date}` (date `YYYY-MM-DD`)

Returns one daily OHLCV bar for **every** US stock on that date. This is the best EOD endpoint for the free tier, because it costs one call however many tickers are watched. The bar for today is not available until after the close. On a weekend or holiday, `results` is empty, so step back to the previous day.

```json
{"status": "OK", "adjusted": true, "resultsCount": 10342,
 "results": [{"T": "AAPL", "o": 189.1, "h": 191.0, "l": 188.4, "c": 190.2, "v": 51234567, "vw": 189.9, "t": 1760731200000, "n": 612345}]}
```

`t` is the window timestamp in milliseconds.

```python
from datetime import date, timedelta

def latest_eod_closes(client: RESTClient, tickers: set[str]) -> dict[str, float]:
    """Close prices from the most recent trading day that has data."""
    day = date.today() - timedelta(days=1)
    for _ in range(5):  # skip weekends/holidays
        bars = client.get_grouped_daily_aggs(day.isoformat(), adjusted=True)
        if bars:
            return {b.ticker: b.close for b in bars if b.ticker in tickers}
        day -= timedelta(days=1)
    return {}
```

SDK model `GroupedDailyAgg`: `ticker, open, high, low, close, volume, vwap, timestamp, transactions`.

Each step back costs one call. On the free tier (5/min), keep the loop short and cache the result. The data only changes once a day.

### 3.4 Previous Close (all plans, one ticker per call)

`GET /v2/aggs/ticker/{ticker}/prev`

```python
prev = client.get_previous_close_agg("AAPL")  # list[PreviousCloseAgg] (one item)
print(prev[0].close, prev[0].timestamp)       # timestamp in ms
```

`PreviousCloseAgg`: `ticker, open, high, low, close, volume, vwap, timestamp`. This uses one call per ticker, so 10 tickers would take 2 minutes on the free tier. Use 3.3 instead for many tickers.

### 3.5 Daily Open/Close for a specific date (all plans)

`GET /v1/open-close/{ticker}/{date}` returns `open, high, low, close, pre_market, after_hours, volume`.

```python
oc = client.get_daily_open_close_agg("AAPL", "2026-10-16")
print(oc.open, oc.close, oc.after_hours)
```

### 3.6 Aggregates (bars over a range, all plans)

`GET /v2/aggs/ticker/{ticker}/range/{multiplier}/{timespan}/{from}/{to}` gives historical bars. It could seed a chart with history. FinAlly does not need it for the core build.

```python
for bar in client.list_aggs("AAPL", 1, "day", "2026-09-01", "2026-10-16", limit=50000):
    print(bar.timestamp, bar.close)
```

`list_aggs` follows pagination automatically. `get_aggs` returns a single page as a list.

### 3.7 Last Trade (Developer+, one ticker)

`GET /v2/last/trade/{ticker}`

```python
trade = client.get_last_trade("AAPL")
print(trade.price, trade.sip_timestamp)  # ns
```

This is one call per ticker. The snapshot (3.1) is strictly better for a watchlist.

### 3.8 WebSockets (Starter+, not used)

`wss://socket.massive.com/stocks` streams trades (`T.AAPL`), quotes (`Q.AAPL`) and per-second or per-minute aggregates (`A.AAPL`, `AM.AAPL`).

```python
from massive import WebSocketClient

ws = WebSocketClient(subscriptions=["AM.AAPL", "AM.MSFT"])  # reads MASSIVE_API_KEY
ws.run(handle_msg=lambda msgs: [print(m) for m in msgs])
```

FinAlly uses REST polling instead (see PLAN.md section 6). It works with every key, needs no long-lived connection, and fits the price cache design.

## 4. Choosing an endpoint for FinAlly

| Need | Endpoint | SDK method | Plan |
|---|---|---|---|
| Live prices, whole watchlist | Full Market Snapshot | `get_snapshot_all(STOCKS, tickers=[...])` | Starter+ |
| EOD prices, whole watchlist | Grouped Daily | `get_grouped_daily_aggs(date)` | All (free OK) |
| Validate one ticker | Single snapshot / prev close | `get_snapshot_ticker` / `get_previous_close_agg` | Starter+ / All |

Price to display from a snapshot, in order of preference:

1. `last_trade.price`: true last trade (Developer+)
2. `min.close`: latest minute bar (Starter+, delayed)
3. `day.close`, if non-zero
4. `prev_day.close`: before the first trade of the day

## 5. Polling cadence

| Plan | Interval | Reason |
|---|---|---|
| Free (EOD) | 15 min, or once at start | Data changes once per day; 5 calls/min limit |
| Starter / Developer | 15 s | Data is 15-min delayed anyway; minute bars change every 60 s |
| Advanced | 2 to 5 s | Real-time; no call limit, so be reasonable |

The SDK client is **synchronous** (urllib3). In asyncio code, call it with `await asyncio.to_thread(client.get_snapshot_all, ...)`.
