# Trading Platform

AI-powered trading dashboard combining technical analysis from Python with reasoning from a large language model. Designed for paper trading — no real money involved.

## Features

- **Watchlist** — track symbols from Hyperliquid (crypto perps) and Yahoo Finance (stocks, ETFs, crypto)
- **Candlestick charts** — real-time and historical OHLCV data via TradingView Lightweight Charts
- **AI signals** — Python computes indicators, LLM generates reasoning and structured buy/sell signals (setup type, time horizon, entry zone, risk/reward, invalidation)
- **Daily brief** — consolidated market overview: regime, top opportunities with entry/stop/target, open positions summary, and risk notes
- **Manual signal execution** — convert buy/sell signals into linked paper trades directly from the dashboard
- **Paper trading** — simulated portfolio with P&L tracking, stop-loss and take-profit
- **Strategy builder** — define and manage custom trading strategies
- **Strategy templates** — create pre-built RSI reversal, MACD trend, Bollinger squeeze, EMA pullback, and volume breakout strategies from the dashboard
- **Risk management** — position sizing calculator for fixed-fractional, volatility/ATR, and quarter-Kelly sizing with max-exposure caps
- **Backtesting dashboard** — review saved backtests with metrics, equity curve, simulated trade log, and quick parameter optimization previews
- **Performance analytics** — portfolio performance dashboard with equity curve, max drawdown, monthly P&L, profit factor, average win/loss, and symbol P&L
- **Browser alerts** — opt-in desktop notifications for high-confidence signals, stale data/worker/LLM warnings, closed paper trades, and new daily briefs
- **Realtime stream** — lightweight WebSocket snapshots for live dashboard status and latest candle updates
- **Trade journal** — log and review paper trades with win rate, realized/unrealized P&L, average win/loss, and risk levels
- **System status** — monitor backend services, Redis, LLM endpoint, Celery worker health, data freshness, daily brief readiness, task recency, and risk limits
- **Scheduled analysis** — automatic analysis of watchlist symbols every 4 hours; daily brief every 24 hours

## Architecture

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  Frontend    │────▶│  Nginx       │────▶│  FastAPI     │
│  React/TS    │     │  (proxy)     │     │  Backend     │
│  Vite        │     │  :80         │     │  :8000       │
└──────────────┘     └──────────────┘     └──────┬───────┘
                                                  │
                              ┌───────────────────┤
                              │                   │
                      ┌───────┴──────┐   ┌────────┴──────┐
                      │  SQLite DB   │   │  Celery Worker │
                      │  (trading.db)│   │  + Redis       │
                      └──────────────┘   └────────┬───────┘
                                                  │
                                        ┌─────────┴─────────┐
                                        │ External Services  │
                                        │  • Hyperliquid WS  │
                                        │  • Yahoo Finance   │
                                        │  • LLM (Qwen3.6-   │
                                        │    35B via         │
                                        │    llama.cpp)      │
                                        └───────────────────┘
```

### Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | React + TypeScript, Vite, TradingView Lightweight Charts |
| **Backend** | Python, FastAPI, SQLModel, SQLite |
| **Worker** | Celery + Redis (scheduled analysis, SL/TP checks, candle collection) |
| **Data** | Hyperliquid WebSocket (crypto perps), Yahoo Finance (stocks/ETFs/crypto) |
| **LLM** | Qwen3.6-35B via external llama.cpp server (OpenAI-compatible API) |
| **Deployment** | Docker Compose, Nginx reverse proxy |

### Services

| Service | Port | Description |
|---------|------|-------------|
| Frontend (Nginx) | 3000 | SPA dashboard with API proxy |
| Backend (FastAPI) | 8000 | REST API, documentation at `/docs` |
| Redis | 6379 | Celery message broker |
| Celery Worker | — | Background tasks (analysis, SL/TP, candle collection) |

### Directory Structure

```
trading-platform/
├── docker-compose.yml       # Full stack: backend, worker, redis, frontend
├── .env.example             # Environment variables template
│
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI app entry point
│   │   ├── config.py        # Settings
│   │   ├── database.py      # SQLModel engine & init
│   │   ├── celery.py        # Celery config
│   │   ├── seed.py          # Seed symbols on startup
│   │   ├── api/             # Route routers (symbols, signals, portfolio, etc.)
│   │   ├── models/          # SQLModel ORM models
│   │   ├── schemas/         # Pydantic request/response schemas
│   │   ├── services/        # Business logic (LLM analysis, backtesting)
│   │   ├── worker/          # Celery task definitions
│   │   └── utils/           # Shared utilities
│   ├── tests/               # Backend tests
│   ├── Dockerfile           # Backend image
│   └── Dockerfile.worker    # Celery worker image
│
├── frontend/
│   ├── nginx.conf           # Nginx reverse proxy config
│   ├── Dockerfile           # Frontend image (nginx + static build)
│   ├── package.json         # Vite + React + TypeScript
│   └── src/
│       ├── App.tsx          # Root dashboard layout
│       ├── components/      # UI panels (chart, daily brief, signals, portfolio, etc.)
│       ├── hooks/           # React data-fetching hooks
│       ├── lib/             # API client
│       └── types/           # TypeScript types
│
└── pytest.ini               # Pytest config for root-level test runs
```

## Quick Start

### Prerequisites

- Docker & Docker Compose
- An external LLM endpoint (OpenAI-compatible) — default is `http://10.50.0.30:8000/v1`
  - If you don't have one, the app will start but AI analysis will be skipped

### 1. Configure Environment

```bash
cp .env.example .env
# Edit .env with your LLM endpoint and secret key
```

Key variables:

| Variable | Description | Example |
|----------|-------------|---------|
| `LLM_BASE_URL` | LLM API base URL | `http://10.50.0.30:8000/v1` |
| `LLM_MODEL` | Model name | `your-model-name` |
| `LLM_API_KEY` | API key (if required) | `sk-...` |
| `SECRET_KEY` | FastAPI secret key | any random string |
| `DATABASE_URL` | SQLite database path | `sqlite:///./data/trading.db` |
| `INITIAL_CAPITAL` | Starting paper trading balance | `10000` |
| `MAX_POSITION_PCT` | Maximum account percentage allocated to each paper trade | `10` |
| `AUTO_TRADE_ENABLED` | Opt-in automatic paper-trade creation from qualifying AI signals | `false` |
| `AUTO_TRADE_MIN_CONFIDENCE` | Minimum signal confidence required when auto-trading is enabled | `65` |
| `MAX_OPEN_TRADES` | Maximum number of simultaneously open paper trades | `5` |
| `MIN_RISK_REWARD_RATIO` | Minimum risk/reward required when auto-trading is enabled | `1.5` |
| `ANALYSIS_INTERVAL_HOURS` | Hours between scheduled analyses | `4` |
| `DAILY_BRIEF_ENABLED` | Enable/disable daily brief generation | `true` |
| `DAILY_BRIEF_INTERVAL_HOURS` | Hours between daily brief generations | `24` |

### 2. Start the Stack

```bash
docker compose up -d --build
```

Services start in order: Redis → Backend → Worker → Frontend.

If another local service already owns port 3000, use a temporary uncommitted override:

```yaml
# docker-compose.override.yml
services:
  frontend:
    ports: !override
      - "3001:80"
```

Then open `http://localhost:3001` for that local smoke test. The committed default remains `http://localhost:3000`.

### 3. Open the Dashboard

```
http://localhost:3000
```

Backend API docs: `http://localhost:8000/docs`

### 4. Stop

```bash
docker compose down
```

## Development

### Backend

```bash
cd backend

# Create a virtual environment (first time)
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run tests
python3 -m pytest -q

# Run the server
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend

# Install dependencies (first time)
npm install

# Start dev server
npm run dev

# Build for production
npm run build
```

### Full verification

```bash
# Backend tests
cd backend && python3 -m pytest -q

# Frontend build
cd frontend && npm run build

# Docker Compose config
docker compose config
```

## API Endpoints

All routes are prefixed with `/api/`. Full interactive docs at `http://localhost:8000/docs`.

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/health` | Service health check |
| GET | `/api/health/status` | Detailed service, data freshness, worker, and risk status |
| GET | `/api/config` | Current configuration |
| GET | `/api/watchlist` | List all watchlist symbols |
| POST | `/api/watchlist` | Add symbol to watchlist |
| DELETE | `/api/watchlist/{symbol_id}` | Remove symbol from the active watchlist |
| POST | `/api/watchlist/seed` | Seed default Hyperliquid and Yahoo Finance symbols |
| GET | `/api/candles/{symbol}` | OHLCV candle data |
| GET | `/api/signals` | List AI-generated signals |
| GET | `/api/signals/{signal_id}` | Get one signal by ID |
| GET | `/api/signals/latest?symbol=SYMBOL` | Latest signal for a symbol |
| POST | `/api/signals/analyze/{symbol}` | Trigger on-demand analysis |
| POST | `/api/signals/{signal_id}/execute` | Create or return a linked paper trade for a buy/sell signal |
| GET | `/api/daily-brief/latest` | Latest daily market brief |
| GET | `/api/daily-brief/history` | Historical daily briefs |
| POST | `/api/daily-brief/generate` | Generate a new daily brief on demand |
| GET | `/api/portfolio/summary` | Portfolio summary and P&L |
| GET | `/api/portfolio/performance` | Portfolio performance analytics, equity curve, drawdown, monthly P&L, and symbol P&L |
| GET | `/api/portfolio` | List paper trades |
| POST | `/api/portfolio` | Create a manual paper trade |
| GET | `/api/risk/profile` | Current risk limits and supported position sizing methods |
| POST | `/api/risk/position-size` | Calculate fixed-fractional, volatility/ATR, or quarter-Kelly position size |
| POST | `/api/trades/check` | Trigger paper trade SL/TP checks |
| GET | `/api/strategies` | List strategies |
| POST | `/api/strategies` | Create a strategy |
| GET | `/api/strategies/templates` | List built-in strategy templates |
| POST | `/api/strategies/templates/{template_id}/create` | Create a strategy from a built-in template |
| GET | `/api/backtest` | List saved backtest results |
| POST | `/api/backtest/run` | Run a backtest |
| POST | `/api/backtest/optimize` | Rank parameter candidates for strategy optimization previews |
| WS | `/ws/stream` | Realtime dashboard snapshot stream |

## Data Sources

### Hyperliquid

- **What:** Crypto perpetual futures (perps)
- **Protocol:** WebSocket
- **Symbols:** Auto-seeded from Hyperliquid's perp list
- **Usage:** Real-time price data, candle collection

### Yahoo Finance

- **What:** Stocks, ETFs, crypto spot
- **Protocol:** REST API
- **Symbols:** Auto-seeded popular symbols (SPY, QQQ, AAPL, BTC-USD, ETH-USD)
- **Usage:** Historical and real-time price data

## AI Analysis Pipeline

1. **Fetch candles** — pull OHLCV data for the symbol
2. **Compute indicators** — Python calculates RSI, MACD, Bollinger Bands, moving averages, volume ratio, and derived strategy-template fields
3. **Format prompt** — structured context with indicators, price action, and trend info
4. **LLM reasoning** — Qwen3.6-35B generates analysis, reasoning, and a normalized JSON signal through an OpenAI-compatible endpoint
5. **Store signal** — result saved to SQLite for frontend display

Analysis runs every 4 hours for all watchlist symbols via Celery Beat. You can also trigger it on demand via the API. The LLM client is created and closed per analysis call so Celery tasks do not leak async HTTP clients across event-loop boundaries.

### Structured Signal Fields

Signals now include structured fields for trade planning:

| Field | Description | Example |
|-------|-------------|---------|
| `setup_type` | Trading setup classification | `breakout`, `pullback`, `reversal`, `momentum` |
| `time_horizon` | Expected holding period | `intraday`, `swing`, `position` |
| `entry_price` | Suggested entry price | `63450.50` |
| `entry_min` / `entry_max` | Entry price range | `63000` - `64000` |
| `risk_reward` | Risk/reward ratio | `2.5` |
| `invalidation` | Condition that invalidates the setup | `Close below 62500` |

### Daily Brief

The daily brief consolidates everything into a morning overview:

- **Market regime** — overall market conditions (bullish, bearish, sideways, volatile)
- **Summary** — narrative overview of the day's landscape
- **Top opportunities** — up to 3 signals with entry, stop, target, and risk/reward
- **Open positions summary** — current open trades, exposure, and unrealized P&L
- **Risk notes** — highlighted risks and things to watch

The daily brief is generated automatically every 24 hours via Celery Beat, or on demand through the API or UI.

### System Status

The `/api/health/status` endpoint now reports:

- Component health: backend, database, Redis, LLM endpoint
- Data freshness: latest candle age, latest signal age, latest daily brief age
- Worker task status: last run timestamps for all scheduled tasks
- Risk limits: auto-trade confidence threshold, max open trades, max position %, min risk/reward

## Paper Trading

- **Simulated balance:** configurable via `INITIAL_CAPITAL` (default: 10,000)
- **Position sizing:** max position percentage configurable via `MAX_POSITION_PCT` (default: 10%)
- **Risk calculator:** `/api/risk/position-size` and the dashboard Risk Manager support fixed-fractional sizing, volatility/ATR sizing, and safer quarter-Kelly sizing. Calculations cap notional exposure to the configured max position percentage unless explicitly overridden in the request.
- **Manual trades:** create paper trades directly from the portfolio API/UI
- **Signal execution:** buy/sell signals can be converted into linked paper trades with `POST /api/signals/{signal_id}/execute`; hold signals are intentionally rejected
- **Optional auto-paper-trading:** automatic paper-trade creation from qualifying signals is available only when `AUTO_TRADE_ENABLED=true`; it is disabled by default so first use stays review-first/manual
- **Stop-loss / Take-profit:** checked every 30 seconds by the Celery worker
- **Trade journal:** all trades logged with entry/exit, P&L, and signal reference

## Realtime Dashboard and Alerts

- `/ws/stream` emits a dashboard snapshot every 5 seconds with the latest candle, latest signal, open position count, and unrealized P&L
- The frontend displays WebSocket connection status and latest streamed candle price in the header
- The frontend includes opt-in browser notifications via the browser Notification API
- Alerts currently fire from dashboard data for high-confidence buy/sell signals, paper trades that close, and new daily briefs

## Strategy Templates

Built-in strategy templates provide ready-to-create rule sets from the Risk & Strategies dashboard panel:

- RSI Reversal
- MACD Trend Continuation
- Bollinger Squeeze Breakout
- EMA Trend Pullback
- Volume Breakout

Templates are available from `GET /api/strategies/templates` and can be converted into saved strategies with `POST /api/strategies/templates/{template_id}/create`.

## Backtesting

- Walk historical candles through a strategy rule set
- Returns: equity curve, win rate, max drawdown, total return, Sharpe ratio
- Run via `POST /api/backtest/run`
- Review saved backtests through the dashboard Backtests tab, including metrics, an equity curve preview, and recent simulated trades
- Use `POST /api/backtest/optimize` or the dashboard optimizer preview to rank parameter candidates before running deeper tests

## Future Work

- [ ] Live trading support (beyond paper)
- [ ] Candle-backed multi-asset parameter optimization and walk-forward testing
- [ ] Backend-managed push notifications beyond browser-local alerts
- [ ] User accounts and multi-user support
- [ ] Additional data sources (CoinGecko, Binance, etc.)

## License

MIT
