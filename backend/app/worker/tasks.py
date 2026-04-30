"""Celery worker tasks for candle collection, AI analysis, and paper trading."""

import asyncio
import json
import logging
from contextlib import contextmanager
from datetime import datetime
from app.utils.time import utc_now
from typing import Iterator

from sqlmodel import Session, select

from app.celery import celery_app
from app.database import engine
from app.models.config import AppConfig
from app.models.candle import Candle
from app.models.paper_trade import PaperTrade
from app.models.symbol import Symbol
from app.services.candle_collector import CandleCollector
from app.services.llm_analysis import LLMAnalysisService
from app.services.yahoo_finance import get_current_price

logger = logging.getLogger(__name__)


@contextmanager
def session_scope() -> Iterator[Session]:
    session = Session(engine)
    try:
        yield session
    finally:
        session.close()


async def _collect_symbol_candles(collector: CandleCollector, symbol: Symbol, timeframe: str) -> int:
    return await collector.collect_symbol(
        symbol=symbol.symbol,
        exchange=symbol.exchange,
        interval=timeframe,
    )


def _latest_price(db: Session, symbol: Symbol) -> float | None:
    if symbol.exchange == "yahoo":
        price = get_current_price(symbol.symbol)
        if price is not None:
            return price

    latest_candle = db.exec(
        select(Candle)
        .where(Candle.symbol_id == symbol.symbol_id)
        .order_by(Candle.timestamp.desc())
        .limit(1)
    ).first()
    return float(latest_candle.close) if latest_candle else None


def _set_task_status(
    db: Session,
    key: str,
    payload: dict,
    description: str,
) -> None:
    record = db.exec(select(AppConfig).where(AppConfig.key == key)).first()
    value = json.dumps(payload)
    if record is None:
        record = AppConfig(key=key, value=value, description=description)
        db.add(record)
    else:
        record.value = value
        record.description = description
        record.updated_at = utc_now()
    db.commit()


@celery_app.task(name="app.worker.tasks.collect_candles")
def collect_candles(timeframe: str = "1h") -> dict:
    logger.info("Collecting candles for active watchlist symbols")
    collector = CandleCollector()
    stored = 0
    processed = 0

    task_result = {"status": "ok", "symbols": 0, "candles_stored": 0, "timeframe": timeframe, "updated_at": utc_now().isoformat()}

    with session_scope() as db:
        symbols = db.exec(select(Symbol).where(Symbol.is_active == True)).all()

    for symbol in symbols:
        try:
            count = asyncio.run(_collect_symbol_candles(collector, symbol, timeframe))
            stored += count
            processed += 1
        except Exception as exc:
            logger.exception("Failed to collect candles for %s: %s", symbol.symbol, exc)

    task_result["symbols"] = processed
    task_result["candles_stored"] = stored
    with session_scope() as db:
        _set_task_status(db, "task.collect_candles", task_result, "Latest candle collection task status")
    return task_result


@celery_app.task(name="app.worker.tasks.fetch_historical_data")
def fetch_historical_data() -> dict:
    return collect_candles()


@celery_app.task(name="app.worker.tasks.analyze_symbol")
def analyze_symbol_task(symbol_id: int, symbol_name: str | None = None, exchange: str | None = None) -> dict:
    with session_scope() as db:
        symbol = db.get(Symbol, symbol_id)
        if not symbol:
            return {"status": "error", "message": f"Symbol {symbol_id} not found"}

        service = LLMAnalysisService()
        signal = asyncio.run(service.analyze_and_store(db, symbol))
        if not signal:
            return {"status": "error", "message": f"Analysis failed for {symbol_name or symbol.symbol}"}

        task_result = {
            "status": "ok",
            "signal_id": signal.id,
            "symbol": symbol.symbol,
            "direction": signal.direction,
            "confidence": signal.confidence,
            "updated_at": utc_now().isoformat(),
        }
        _set_task_status(db, f"task.analyze_symbol.{symbol.symbol}", task_result, "Latest one-off symbol analysis task status")
        return task_result


@celery_app.task(name="app.worker.tasks.analyze_watchlist")
def analyze_watchlist(timeframe: str = "1h") -> dict:
    logger.info("Running watchlist analysis")
    generated = 0

    task_result = {"status": "ok", "signals_generated": 0, "timeframe": timeframe, "updated_at": utc_now().isoformat()}

    with session_scope() as db:
        symbols = db.exec(select(Symbol).where(Symbol.is_active == True)).all()
        service = LLMAnalysisService()

        for symbol in symbols:
            try:
                signal = asyncio.run(service.analyze_and_store(db, symbol, timeframe=timeframe))
                if signal:
                    generated += 1
            except Exception as exc:
                logger.exception("Failed to analyze %s: %s", symbol.symbol, exc)
                db.rollback()

        task_result["signals_generated"] = generated
        _set_task_status(db, "task.analyze_watchlist", task_result, "Latest watchlist analysis task status")

    return task_result


@celery_app.task(name="app.worker.tasks.analyze_all_signals")
def analyze_all_signals(timeframe: str = "1h") -> dict:
    return analyze_watchlist(timeframe=timeframe)


@celery_app.task(name="app.worker.tasks.check_sl_tp")
def check_sl_tp() -> dict:
    logger.info("Checking open paper trades against stop-loss / take-profit")
    closed = 0

    task_result = {"status": "ok", "closed_trades": 0, "updated_at": utc_now().isoformat()}

    with session_scope() as db:
        open_trades = db.exec(select(PaperTrade).where(PaperTrade.status == "open")).all()

        for trade in open_trades:
            symbol = db.get(Symbol, trade.symbol_id)
            if not symbol:
                continue

            price = _latest_price(db, symbol)
            if price is None:
                continue

            trade.current_price = round(price, 8)
            trade.pnl = 0.0
            trade.pnl_pct = 0.0
            if trade.direction == "long":
                unrealized = (price - trade.entry_price) * trade.quantity
            else:
                unrealized = (trade.entry_price - price) * trade.quantity
            trade.pnl = round(unrealized, 2)
            trade.pnl_pct = round((unrealized / (trade.entry_price * trade.quantity)) * 100, 2) if trade.entry_price else 0.0

            exit_price = None
            status = "open"
            if trade.direction == "long":
                if trade.stop_loss is not None and price <= trade.stop_loss:
                    status = "sl_hit"
                    exit_price = trade.stop_loss
                elif trade.take_profit is not None and price >= trade.take_profit:
                    status = "tp_hit"
                    exit_price = trade.take_profit
                elif trade.take_profit_2 is not None and price >= trade.take_profit_2:
                    status = "tp_hit"
                    exit_price = trade.take_profit_2
            else:
                if trade.stop_loss is not None and price >= trade.stop_loss:
                    status = "sl_hit"
                    exit_price = trade.stop_loss
                elif trade.take_profit is not None and price <= trade.take_profit:
                    status = "tp_hit"
                    exit_price = trade.take_profit
                elif trade.take_profit_2 is not None and price <= trade.take_profit_2:
                    status = "tp_hit"
                    exit_price = trade.take_profit_2

            if status != "open" and exit_price is not None:
                if trade.direction == "long":
                    realized = (exit_price - trade.entry_price) * trade.quantity
                else:
                    realized = (trade.entry_price - exit_price) * trade.quantity
                trade.status = status
                trade.exit_price = exit_price
                trade.exit_time = utc_now()
                trade.current_price = exit_price
                trade.close_reason = status
                trade.pnl = round(realized, 2)
                trade.pnl_pct = round((realized / (trade.entry_price * trade.quantity)) * 100, 2) if trade.entry_price else 0.0
                closed += 1

        db.commit()
        task_result["closed_trades"] = closed
        _set_task_status(db, "task.check_sl_tp", task_result, "Latest paper trade stop-loss/take-profit task status")

    return task_result


@celery_app.task(name="app.worker.tasks.check_paper_trades")
def check_paper_trades() -> dict:
    return check_sl_tp()
