# Trading Platform

AI-powered trading dashboard combining technical analysis from Python with reasoning from a large language model. Designed for paper trading — no real money involved.

## Features

- **Watchlist** — track symbols from Hyperliquid (crypto perps) and Yahoo Finance (stocks, ETFs, crypto)
- **Candlestick charts** — real-time and historical OHLCV data via TradingView Lightweight Charts
- **AI signals** — Python computes indicators, LLM generates reasoning and buy/sell signals
- **Paper trading** — simulated portfolio with P&L tracking, stop-loss and take-profit
- **Strategy builder** — define and manage custom trading strategies
- **Backtesting** — walk historical candles through a strategy and get metrics (win rate, Sharpe, max drawdown)
- **Trade journal** — log and review past paper trades
- **System status** — monitor backend services, Redis, LLM endpoint, and Celery worker health
- **Scheduled analysis** — automatic analysis of watchlist symbols every 4 hours

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
│       ├── components/      # UI panels (chart, signals, portfolio, etc.)
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
| `ANALYSIS_INTERVAL_HOURS` | Hours between scheduled analyses | `4` |

### 2. Start the Stack

```bash
docker compose up -d --build
```

Services start in order: Redis → Backend → Worker → Frontend.

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
| GET | `/api/config` | Current configuration |
| GET | `/api/symbols` | List all watchlist symbols |
| GET | `/api/symbols/{symbol}` | Symbol detail |
| POST | `/api/symbols` | Add symbol to watchlist |
| DELETE | `/api/symbols/{symbol}` | Remove symbol |
| GET | `/api/candles/{symbol}` | OHLCV candle data |
| GET | `/api/signals` | List AI-generated signals |
| GET | `/api/signals/{symbol}` | Latest signals for a symbol |
| POST | `/api/signals/analyze/{symbol}` | Trigger on-demand analysis |
| GET | `/api/portfolio` | Portfolio summary and P&L |
| POST | `/api/portfolio/trade` | Execute a paper trade |
| GET | `/api/strategies` | List strategies |
| POST | `/api/strategies` | Create a strategy |
| POST | `/api/backtest` | Run a backtest |

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
2. **Compute indicators** — Python calculates RSI, MACD, Bollinger Bands, moving averages, etc.
3. **Format prompt** — structured context with indicators, price action, and trend info
4. **LLM reasoning** — Qwen3.6-35B generates analysis, reasoning, and a signal
5. **Store signal** — result saved to SQLite for frontend display

Analysis runs every 4 hours for all watchlist symbols via Celery Beat. You can also trigger it on demand via the API.

## Paper Trading

- **Simulated balance:** configurable via `INITIAL_CAPITAL` (default: 10,000)
- **Position sizing:** max position percentage configurable via `MAX_POSITION_PCT` (default: 10%)
- **Stop-loss / Take-profit:** checked every 30 seconds by the Celery worker
- **Trade journal:** all trades logged with entry/exit, P&L, and signal reference

## Backtesting

- Walk historical candles through a strategy rule set
- Returns: equity curve, win rate, max drawdown, total return, Sharpe ratio
- Run via API or through the dashboard UI

## Future Work

- [ ] Live trading support (beyond paper)
- [ ] More technical indicators and strategy templates
- [ ] Real-time WebSocket price updates in the frontend
- [ ] User accounts and multi-user support
- [ ] Alerting (email, Telegram, push notifications)
- [ ] Advanced risk management (position sizing algorithms)
- [ ] Performance dashboards and analytics
- [ ] Additional data sources (CoinGecko, Binance, etc.)

## License

MIT
