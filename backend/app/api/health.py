import json
from datetime import datetime
from app.utils.time import utc_now

import httpx
import redis
from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.config import settings
from app.database import get_db
from app.models.candle import Candle
from app.models.config import AppConfig
from app.models.symbol import Symbol

router = APIRouter()


@router.get("/health")
async def health_check():
    return {"status": "ok", "service": "trading-platform-backend"}


@router.get("/health/status")
async def system_status(db: Session = Depends(get_db)):
    latest_candle = db.exec(
        select(Candle, Symbol)
        .join(Symbol, Symbol.symbol_id == Candle.symbol_id)
        .order_by(Candle.timestamp.desc())
        .limit(1)
    ).first()

    task_rows = db.exec(
        select(AppConfig).where(AppConfig.key.like("task.%")).order_by(AppConfig.updated_at.desc())
    ).all()
    tasks = {}
    for row in task_rows:
        try:
            tasks[row.key] = json.loads(row.value)
        except json.JSONDecodeError:
            tasks[row.key] = {"raw": row.value}

    redis_ok = False
    try:
        client = redis.from_url(settings.redis_url)
        redis_ok = bool(client.ping())
    except Exception:
        redis_ok = False

    llm_ok = False
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                f"{settings.llm_base_url.rstrip('/')}/models",
                headers={"Authorization": f"Bearer {settings.llm_api_key}"},
            )
            llm_ok = response.status_code < 500
    except Exception:
        llm_ok = False

    candle_status = None
    if latest_candle:
        candle, symbol = latest_candle
        age_seconds = int((utc_now() - candle.timestamp.replace(tzinfo=None)).total_seconds())
        candle_status = {
            "symbol": symbol.symbol,
            "exchange": symbol.exchange,
            "timestamp": candle.timestamp.isoformat(),
            "age_seconds": age_seconds,
            "fresh": age_seconds <= 60 * 60 * 6,
        }

    return {
        "status": "ok" if redis_ok else "degraded",
        "components": {
            "backend": True,
            "redis": redis_ok,
            "llm_endpoint": llm_ok,
        },
        "latest_candle": candle_status,
        "tasks": tasks,
        "analysis_interval_hours": settings.analysis_interval_hours,
        "risk_limits": {
            "auto_trade_min_confidence": settings.auto_trade_min_confidence,
            "max_open_trades": settings.max_open_trades,
            "max_position_pct": settings.max_position_pct,
            "min_risk_reward_ratio": settings.min_risk_reward_ratio,
        },
    }
