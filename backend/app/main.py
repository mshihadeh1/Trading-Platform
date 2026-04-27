"""Trading Platform - FastAPI Backend"""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.config import settings
from app.database import init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing Trading Platform...")
    init_db()
    logger.info("Database initialized.")
    yield
    logger.info("Trading Platform shut down.")


app = FastAPI(
    title="Trading Platform",
    description="AI-powered trading decision support system",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*", "http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- Include routers (avoid duplicates) ----
from app.api import symbols, candles, config as config_api, health, portfolio, strategies, backtest, signals
from app.api import assets, trade

app.include_router(symbols.router, prefix="/api/watchlist", tags=["watchlist"])
app.include_router(candles.router, prefix="/api/candles", tags=["candles"])
app.include_router(config_api.router, prefix="/api/config", tags=["config"])
app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(portfolio.router, prefix="/api/portfolio", tags=["portfolio"])
app.include_router(strategies.router, prefix="/api/strategies", tags=["strategies"])
app.include_router(backtest.router, prefix="/api/backtest", tags=["backtest"])

# These routers already define their own prefix in the router definition
app.include_router(assets.router)        # prefix="/api/assets" → /api/assets
app.include_router(trade.router)         # prefix="/api/trades" → /api/trades

# These need a prefix added in main.py
app.include_router(signals.router, prefix="/api")  # → /api/signals

# Health
@app.get("/api/health")
def health_check():
    return {"status": "ok", "service": "trading-platform"}


@app.get("/api/config")
def config():
    return {
        "llm_model": settings.llm_model,
        "analysis_interval_hours": settings.analysis_interval_hours,
        "initial_capital": settings.initial_capital,
    }


# ---- SPA fallback for frontend ----
FRONTEND_DIST = os.path.join(os.path.dirname(__file__), "../../frontend/dist")

if os.path.exists(FRONTEND_DIST):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIST), name="static")


@app.get("/{path:path}")
async def catch_all(path: str):
    index_path = os.path.join(FRONTEND_DIST, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"error": "Frontend not built"}
