# Trading Platform — Hybrid Architecture Implementation Plan

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                        FRONTEND (React)                         │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────────────────┐ │
│  │ Sidebar  │ │  Chart   │ │ Signals  │ │ Portfolio / Trades │ │
│  │ (Watch- │ │(Lightwt- │ │ Panel   │ │ (Paper Trading)    │ │
│  │  list)  │ │  h Charts│ │ (AI sig- │ │                    │ │
│  │         │ │  from TV) │ │  nals)   │ │                    │ │
│  └──────────┘ └──────────┘ └──────────┘ └────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
         │                    │              │
         ▼                    ▼              ▼
┌──────────────────────────────────────────────────────────────────┐
│                     BACKEND (FastAPI)                           │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌──────────────┐ │
│  │ Symbol/    │ │ Candles    │ │ Signals    │ │ Portfolio/   │ │
│  │ Watchlist  │ │ API        │ │ API        │ │ Trades       │ │
│  └────────────┘ └────────────┘ └────────────┘ └──────────────┘ │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌──────────────┐ │
│  │ Indicators │ │ LLM        │ │ Backtest   │ │ Paper Trade  │ │
│  │ Engine     │ │ Analysis   │ │ Engine     │ │ Monitor      │ │
│  └────────────┘ └────────────┘ └────────────┘ └──────────────┘ │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  Celery Worker (Scheduled Analysis + SL/TP Checks)         │ │
│  └────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
         │                    │
         ▼                    ▼
┌──────────────┐    ┌────────────────┐
│ Hyperliquid  │    │ Yahoo Finance  │
│ WebSocket    │    │ REST API       │
└──────────────┘    └────────────────┘
```

## Phase 1 — Fix & Stabilize (Week 1)

### 1.1 Clean up duplicate routers
- **Problem:** `api/strategy.py` and `api/strategies.py` both define routes at `/api/strategies/`
- **Solution:** Delete `api/strategy.py` (the legacy one). Keep `api/strategies.py` which uses the new schema with `is_active`, `timeframe`, `exchange`.
- **Fix:** Remove `api/strategy` import from `main.py`.

### 1.2 Fix frontend type mismatch
- **Problem:** `frontend/src/types.ts` defines `Signal` with `asset_symbol`, but `frontend/src/types/index.ts` defines `Signal` with `symbol`. Components use `types/index.ts`.
- **Solution:** 
  1. Rename `types/index.ts` → `types/api.ts` and make it the canonical API types
  2. Keep `types.ts` as re-exports for backwards compat, fixing the `Signal` interface to match backend
  3. Or: make the backend API response consistent by aliasing `asset_symbol` → `symbol` in the JSON response

### 1.3 Fix API path prefix issues
- **Problem:** Frontend `api.ts` has `BASE = '/api'` then prefixes paths with `/api/watchlist` — resulting in `/api/api/watchlist`
- **Solution:** Remove the `BASE` prefix from internal API paths. The Vite proxy already handles `/api` → `http://backend:8000`.

### 1.4 Fix nginx proxy path
- **Problem:** nginx.conf proxies `/api/` but FastAPI routes already include `/api/` prefix
- **Solution:** Change nginx to proxy `/api` (without trailing slash) and ensure backend routes don't double-prefix.

### 1.5 Fix Docker build
- **Problem:** `Dockerfile.worker` is missing; backend Dockerfile may have issues
- **Solution:** Create worker Dockerfile, ensure `requirements.txt` includes celery, websockets, yfinance, pandas, ta

## Phase 2 — Data Pipeline (Week 1-2)

### 2.1 Add Candle model & DB schema
```python
class Candle(SQLModel, table=True):
    candle_id: Optional[int] = Field(primary_key=True)
    symbol_id: int = Field(foreign_key="symbols.symbol_id")
    timeframe: str  # "1m", "5m", "15m", "1h", "4h", "1d"
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
```

### 2.2 Build Candle Data Collector Service
New service: `backend/app/services/candle_collector.py`
- Fetches candles from Hyperliquid (perps) and Yahoo Finance (stocks/ETFs/crypto)
- Stores them in the `candles` table
- Runs every 5 minutes via Celery beat

### 2.3 Add initial symbol seeding
- Auto-seed Hyperliquid perpetual pairs on first run
- Add popular Yahoo Finance symbols (SPY, QQQ, AAPL, BTC-USD, etc.)
- Endpoint: `POST /api/symbols/seed`

### 2.4 Watchlist API
- New unified watchlist endpoint at `/api/watchlist`
- GET: list all watchlist symbols (both Hyperliquid + Yahoo)
- POST: add a symbol (auto-detect exchange)
- DELETE: remove a symbol
- Frontend `api.ts` calls match this structure

## Phase 3 — AI Analysis Pipeline (Week 2-3)

### 3.1 Enhance Indicators Service
`backend/app/services/indicators.py` — improve to return structured data:
- RSI (14), MACD (12,26,9), Bollinger Bands (20,2), EMA (9,21,50)
- Volume ratio (20-day), ATR (14), funding rate (Hyperliquid)
- Support multiple timeframes (1h, 4h)
- Return normalized indicator values for LLM consumption

### 3.2 LLM Analysis Service improvements
`backend/app/services/llm_analysis.py`:
- Add retry with exponential backoff (3 attempts)
- Add JSON parsing fallback (regex extraction if full parse fails)
- Add timeout (15s per request)
- Create `analyze_and_store()` method that:
  1. Fetches latest candles from DB
  2. Computes indicators
  3. Formats prompt with indicator values + price action + volume
  4. Calls LLM
  5. Stores signal in DB
  6. Returns signal to caller

### 3.3 Celery scheduled analysis
- Every 4 hours: analyze all active watchlist symbols
- On-demand: `POST /api/signals/analyze/{symbol}` for manual trigger
- Each analysis produces a Signal record

## Phase 4 — Paper Trading (Week 3)

### 4.1 Paper Trade API
`backend/app/api/portfolio.py` — already exists but needs fixes:
- Fix portfolio summary (use PaperTrade model properly)
- Add auto-execute on signal: when AI signal is buy/hold, auto-create paper position

### 4.2 SL/TP Monitor
Celery worker task:
- Every 30 seconds: check all open paper trades
- Compare current price vs SL/TP
- Close position when hit, record P&L
- Update status to `sl_hit` or `tp_hit`

## Phase 5 — Backtesting (Week 3-4)

### 5.1 Wire up real backtest engine
- `api/backtest.py` currently returns stub data
- Replace with actual `backtest.py` engine execution
- Frontend: add backtest results page showing equity curve + metrics

### 5.2 Backtest Results API
- GET `/api/backtests` — list all backtest runs
- POST `/api/backtests/run` — run backtest on a strategy
- GET `/api/backtests/{id}` — get results with equity curve data

## Phase 6 — Frontend Fixes (Week 2-3)

### 6.1 Fix `types.ts` → `types/index.ts` inconsistency
- Canonical types live in `types/index.ts`
- Signal uses `symbol` not `asset_symbol`
- Fix backend API to return `symbol` instead of `asset_symbol`

### 6.2 Fix `api.ts` API paths
- Remove double `/api` prefix from all paths
- Use relative paths: `/watchlist`, `/candles/`, `/signals/`, `/trades/`, `/portfolio/`

### 6.3 SignalsPanel fix
- Uses `signal.symbol` but backend returns `asset_symbol`
- Fix to use `asset_symbol` or rename in API response

### 6.4 PortfolioPanel fix
- Uses `trades` from `portfolio.list()` but backend has `/api/trades/` and `/api/portfolio/summary/`
- Align frontend hooks with actual API structure

## Phase 7 — Docker & Deployment (Week 4)

### 7.1 Docker Compose
- Backend service (FastAPI + uvicorn)
- Worker service (Celery worker + beat)
- Redis service
- Frontend service (nginx serving built React)

### 7.2 Environment variables
- `.env` for local development
- `database_url=sqlite:///./data/trading.db`
- `llm_base_url=http://host.docker.internal:8000/v1` (for local Docker)

### 7.3 Health check & monitoring
- `/api/health` endpoint
- Check DB connectivity, Redis, LLM endpoint

---

## Priority Order

1. **Phase 1** (Fix critical bugs) — can't build anything without stable base
2. **Phase 2** (Data pipeline) — need data before AI analysis
3. **Phase 3** (AI analysis) — core value proposition
4. **Phase 4** (Paper trading) — second core feature
5. **Phase 5** (Backtesting) — third core feature
6. **Phase 6** (Frontend fixes) — makes everything usable
7. **Phase 7** (Docker) — deployment

## Key Design Decisions

- **Lightweight Charts (TradingView)** for candlestick rendering — already in package.json
- **SQLite** for DB (simple, no extra services needed)
- **Celery + Redis** for scheduled tasks (analysis every 4h, SL/TP every 30s)
- **Qwen 3.6 35B** via llama.cpp for LLM reasoning
- **One canonical types file** in `types/index.ts` to avoid future mismatches
- **Backend API paths match frontend expectations** — no double-prefixing
