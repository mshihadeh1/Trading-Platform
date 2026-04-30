import json
from app.utils.time import utc_now

import httpx
import redis
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlmodel import Session, select

from app.config import settings
from app.database import get_db
from app.models.candle import Candle
from app.models.config import AppConfig
from app.models.daily_brief import DailyBrief
from app.models.signal import Signal
from app.models.symbol import Symbol

router = APIRouter()


@router.get("/health")
async def health_check():
    return {"status": "ok", "service": "trading-platform-backend"}


@router.get("/health/status")
async def system_status(db: Session = Depends(get_db)):
    database_status = _database_status(db)
    redis_status = _redis_status()
    llm_status = await _llm_status()
    candle_status = _latest_candle_status(db)
    signal_status = _latest_signal_status(db)
    daily_brief_status = _latest_daily_brief_status(db)
    tasks = _task_statuses(db)

    core_ok = all(
        component["status"] == "ok"
        for component in [database_status, redis_status, llm_status]
    )

    return {
        "status": "ok" if core_ok else "degraded",
        "components": {
            "backend": {"status": "ok"},
            "database": database_status,
            "redis": redis_status,
            "llm": llm_status,
            # Backward-compatible boolean keys for existing frontend code.
            "llm_endpoint": llm_status["status"] == "ok",
        },
        "data": candle_status,
        "signals": signal_status,
        "daily_brief": daily_brief_status,
        "latest_candle": {
            "symbol": candle_status.get("symbol"),
            "exchange": candle_status.get("exchange"),
            "timestamp": candle_status.get("latest_candle_at"),
            "age_seconds": candle_status.get("age_seconds"),
            "fresh": candle_status.get("fresh"),
        } if candle_status.get("latest_candle_at") else None,
        "tasks": tasks,
        "worker": _worker_status(tasks),
        "analysis_interval_hours": settings.analysis_interval_hours,
        "risk_limits": {
            "auto_trade_min_confidence": settings.auto_trade_min_confidence,
            "max_open_trades": settings.max_open_trades,
            "max_position_pct": settings.max_position_pct,
            "min_risk_reward_ratio": settings.min_risk_reward_ratio,
        },
    }


def _database_status(db: Session) -> dict:
    try:
        db.exec(text("SELECT 1")).one()
        return {"status": "ok"}
    except Exception as exc:
        return {"status": "error", "message": str(exc)}


def _redis_status() -> dict:
    try:
        client = redis.from_url(settings.redis_url)
        return {"status": "ok" if client.ping() else "error"}
    except Exception as exc:
        return {"status": "error", "message": str(exc)}


async def _llm_status() -> dict:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                f"{settings.llm_base_url.rstrip('/')}/models",
                headers={"Authorization": f"Bearer {settings.llm_api_key}"},
            )
            return {
                "status": "ok" if response.status_code < 500 else "error",
                "status_code": response.status_code,
                "base_url": settings.llm_base_url,
                "model": settings.llm_model,
            }
    except Exception as exc:
        return {"status": "error", "message": str(exc), "base_url": settings.llm_base_url, "model": settings.llm_model}


def _latest_candle_status(db: Session) -> dict:
    latest_candle = db.exec(
        select(Candle, Symbol)
        .join(Symbol, Symbol.symbol_id == Candle.symbol_id)
        .order_by(Candle.timestamp.desc())
        .limit(1)
    ).first()
    if not latest_candle:
        return {"latest_candle_at": None, "fresh": False}

    candle, symbol = latest_candle
    age_seconds = int((utc_now() - candle.timestamp.replace(tzinfo=None)).total_seconds())
    return {
        "symbol": symbol.symbol,
        "exchange": symbol.exchange,
        "latest_candle_at": candle.timestamp.isoformat(),
        "age_seconds": age_seconds,
        "fresh": age_seconds <= 60 * 60 * 6,
    }


def _latest_signal_status(db: Session) -> dict:
    latest_signal = db.exec(select(Signal).order_by(Signal.timestamp.desc()).limit(1)).first()
    if not latest_signal or not latest_signal.timestamp:
        return {"latest_signal_at": None, "fresh": False}
    age_seconds = int((utc_now() - latest_signal.timestamp.replace(tzinfo=None)).total_seconds())
    return {
        "latest_signal_at": latest_signal.timestamp.isoformat(),
        "symbol": latest_signal.symbol,
        "direction": latest_signal.direction,
        "confidence": latest_signal.confidence,
        "age_seconds": age_seconds,
        "fresh": age_seconds <= settings.analysis_interval_hours * 60 * 60 * 2,
    }


def _latest_daily_brief_status(db: Session) -> dict:
    latest_brief = db.exec(select(DailyBrief).order_by(DailyBrief.created_at.desc()).limit(1)).first()
    if not latest_brief:
        return {"latest_brief_at": None, "fresh": False}
    age_seconds = int((utc_now() - latest_brief.created_at.replace(tzinfo=None)).total_seconds())
    return {
        "latest_brief_at": latest_brief.created_at.isoformat(),
        "brief_date": latest_brief.brief_date.isoformat(),
        "market_regime": latest_brief.market_regime,
        "age_seconds": age_seconds,
        "fresh": latest_brief.brief_date == utc_now().date(),
    }


def _task_statuses(db: Session) -> dict:
    task_rows = db.exec(
        select(AppConfig).where(AppConfig.key.like("task.%")).order_by(AppConfig.updated_at.desc())
    ).all()
    tasks = {}
    for row in task_rows:
        try:
            tasks[row.key] = json.loads(row.value)
        except json.JSONDecodeError:
            tasks[row.key] = {"raw": row.value}
    return tasks


def _worker_status(tasks: dict) -> dict:
    latest_update = None
    for payload in tasks.values():
        updated_at = payload.get("updated_at") if isinstance(payload, dict) else None
        if updated_at and (latest_update is None or updated_at > latest_update):
            latest_update = updated_at
    return {
        "status": "ok" if latest_update else "unknown",
        "last_heartbeat_at": latest_update,
    }
