"""Celery worker tasks for the trading platform."""

import json
import logging
import asyncio
from datetime import datetime, timezone

from app.celery import celery_app as shared_task
from sqlmodel import Session, select

from app.database import engine
from app.models.candle import Candle
from app.models.symbol import Symbol
from app.models.signal import Signal
from app.models.paper_trade import PaperTrade
from app.services.hyperliquid import get_candles, get_perpetual_symbols, get_info
from app.services.yahoo_finance import get_candles as yf_candles
from app.services.yahoo_finance import YAHOO_POPULAR, get_current_price
from app.services.indicators import compute
from app.services.llm import analyze_symbol

logger = logging.getLogger(__name__)


def _get_db():
    """Context manager to get a database session."""
    with Session(engine) as session:
        yield session


def _store_candles(symbol: str, candles: list):
    """Store candles in the database, skipping duplicates."""
    with _get_db() as db:
        sym = db.exec(select(Symbol).where(Symbol.symbol == symbol)).first()
        if not sym:
            logger.warning(f"No symbol found for {symbol}, skipping candle storage")
            return

        for candle in candles:
            ts = candle["timestamp"]
            if isinstance(ts, (int, float)):
                from datetime import datetime as dt
                ts = dt.fromtimestamp(ts, tz=timezone.utc)

            existing = db.exec(
                select(Candle).where(
                    Candle.symbol_id == sym.symbol_id,
                    Candle.timestamp == ts,
                )
            ).first()
            if not existing:
                db.add(Candle(
                    symbol_id=sym.symbol_id,
                    timestamp=ts,
                    open=candle["open"],
                    high=candle["high"],
                    low=candle["low"],
                    close=candle["close"],
                    volume=candle["volume"],
                ))
        db.commit()


@shared_task(name="worker.tasks.fetch_historical_data")
def fetch_historical_data():
    """Fetch and store historical candles for all watched symbols."""
    logger.info("Starting historical data fetch...")
    total = 0

    # Fetch Hyperliquid perps (running async tasks in sync context)
    perps = asyncio.run(_fetch_all_async())
    for symbol, candles in perps.items():
        try:
            _store_candles(symbol, candles)
            total += len(candles)
        except Exception as e:
            logger.error(f"Failed to store candles for {symbol}: {e}")

    # Fetch Yahoo Finance symbols
    for yahoo_symbol in YAHOO_POPULAR:
        sym_name = yahoo_symbol["symbol"]
        try:
            candles = asyncio.run(yf_candles(sym_name, period="2y", interval="1h"))
            _store_candles(sym_name, candles)
            total += len(candles)
        except Exception as e:
            logger.error(f"Failed to fetch candles for {sym_name}: {e}")

    logger.info(f"Historical data fetch complete: {total} candles stored")
    return {"status": "ok", "candles_fetched": total}


async def _fetch_all_async():
    """Async helper: fetch candles for all Hyperliquid perps."""
    perps = get_perpetual_symbols()
    tasks = []
    for perp in perps:
        tasks.append(get_candles(perp["symbol"], interval="1h", limit=200))
    results = await asyncio.gather(*tasks, return_exceptions=True)

    data = {}
    for (perp, result) in zip(perps, results):
        sym = perp["symbol"]
        if isinstance(result, Exception):
            logger.error(f"Failed to fetch {sym}: {result}")
        else:
            data[sym] = result
    return data


@shared_task(name="worker.tasks.analyze_symbol")
def analyze_symbol_task(symbol_id: int, symbol: str, exchange: str):
    """Run AI analysis on a single symbol."""
    logger.info(f"Starting AI analysis for {symbol}...")

    try:
        with _get_db() as db:
            stmt = (
                select(Candle)
                .where(Candle.symbol_id == symbol_id)
                .order_by(Candle.timestamp.desc())
                .limit(100)
            )
            candles = db.exec(stmt).all()
            if not candles or len(candles) < 50:
                logger.warning(f"Insufficient data for {symbol}: {len(candles) if candles else 0} candles")
                return {"status": "error", "message": "Insufficient data"}

            # Convert SQLModel objects to dicts for indicators
            candle_dicts = [
                {
                    "timestamp": c.timestamp,
                    "open": c.open,
                    "high": c.high,
                    "low": c.low,
                    "close": c.close,
                    "volume": c.volume,
                }
                for c in candles
            ]
            candle_dicts.reverse()

            indicators = compute(candle_dicts)
            latest = candle_dicts[-1]
            close = float(latest["close"])
            context = f"Current price: ${close:.2f}"

            result = asyncio.run(
                analyze_symbol(
                    symbol=symbol,
                    indicators=indicators,
                    price_action=indicators.get("price_action_summary", ""),
                    context=context,
                    exchange=exchange,
                    timeframe="1h",
                )
            )

            if result:
                signal = Signal(
                    symbol_id=symbol_id,
                    symbol=symbol,
                    exchange=exchange,
                    direction=result.get("direction", "hold"),
                    entry_price=result.get("entry_price"),
                    stop_loss=result.get("stop_loss"),
                    take_profit=result.get("take_profit"),
                    take_profit_2=result.get("take_profit_2"),
                    confidence=result.get("confidence", 0),
                    reasoning=result.get("reasoning", ""),
                    indicators_data=json.dumps(indicators),
                    llm_model="Qwen3.6-35B-A3B-UD-Q3_K_S.gguf",
                    analysis_type="ai",
                    raw_response=json.dumps(result),
                )
                db.add(signal)
                db.commit()
                logger.info(f"Signal for {symbol}: {result.get('direction')} (confidence {result.get('confidence', 0)})")
                return {"status": "ok", "direction": result.get("direction")}
            else:
                return {"status": "error", "message": "LLM analysis failed"}

    except Exception as e:
        logger.error(f"Failed to analyze {symbol}: {e}")
        return {"status": "error", "message": str(e)}


@shared_task(name="worker.tasks.analyze_all_signals")
def analyze_all_signals():
    """Run AI analysis on all active symbols."""
    logger.info("Starting AI signal analysis...")
    analyzed = 0

    try:
        with _get_db() as db:
            symbols = db.exec(select(Symbol).where(Symbol.is_active == True)).all()

            for sym in symbols:
                try:
                    stmt = (
                        select(Candle)
                        .where(Candle.symbol_id == sym.symbol_id)
                        .order_by(Candle.timestamp.desc())
                        .limit(100)
                    )
                    candles = db.exec(stmt).all()
                    if not candles or len(candles) < 50:
                        continue

                    candle_dicts = [
                        {
                            "timestamp": c.timestamp,
                            "open": c.open,
                            "high": c.high,
                            "low": c.low,
                            "close": c.close,
                            "volume": c.volume,
                        }
                        for c in candles
                    ]
                    candle_dicts.reverse()

                    indicators = compute(candle_dicts)
                    latest = candle_dicts[-1]
                    close = float(latest["close"])
                    context = f"Current price: ${close:.2f}"

                    result = asyncio.run(
                        analyze_symbol(
                            symbol=sym.symbol,
                            indicators=indicators,
                            price_action=indicators.get("price_action_summary", ""),
                            context=context,
                            exchange=sym.exchange,
                            timeframe="1h",
                        )
                    )

                    if result:
                        signal = Signal(
                            symbol_id=sym.symbol_id,
                            symbol=sym.symbol,
                            exchange=sym.exchange,
                            direction=result.get("direction", "hold"),
                            entry_price=result.get("entry_price"),
                            stop_loss=result.get("stop_loss"),
                            take_profit=result.get("take_profit"),
                            take_profit_2=result.get("take_profit_2"),
                            confidence=result.get("confidence", 0),
                            reasoning=result.get("reasoning", ""),
                            indicators_data=json.dumps(indicators),
                            llm_model="Qwen3.6-35B-A3B-UD-Q3_K_S.gguf",
                            analysis_type="ai",
                            raw_response=json.dumps(result),
                        )
                        db.add(signal)
                        db.commit()
                        analyzed += 1
                        logger.info(f"Signal for {sym.symbol}: {result.get('direction')} (confidence {result.get('confidence', 0)})")

                except Exception as e:
                    logger.error(f"Failed to analyze {sym.symbol}: {e}")

    except Exception as e:
        logger.error(f"Database error during analysis: {e}")

    logger.info(f"Signal analysis complete: {analyzed} signals generated")
    return {"status": "ok", "analyzed": analyzed}


@shared_task(name="worker.tasks.check_paper_trades")
def check_paper_trades():
    """Check open paper trades for stop-loss and take-profit hits."""
    logger.info("Checking paper trades for SL/TP hits...")
    checked = 0

    try:
        with _get_db() as db:
            open_trades = db.exec(
                select(PaperTrade).where(PaperTrade.status == "open")
            ).all()

            for trade in open_trades:
                try:
                    sym = db.exec(
                        select(Symbol).where(Symbol.symbol_id == trade.symbol_id)
                    ).first()
                    if not sym:
                        continue

                    symbol = sym.symbol
                    price = get_current_price(symbol)
                    if price is None:
                        stmt = (
                            select(Candle)
                            .where(Candle.symbol_id == trade.symbol_id)
                            .order_by(Candle.timestamp.desc())
                            .limit(1)
                        )
                        latest = db.exec(stmt).first()
                        if latest:
                            price = float(latest.close)
                        else:
                            continue

                    pnl = 0.0
                    pnl_pct = 0.0
                    status = "open"
                    exit_price = None
                    exit_time = None

                    # Check stop loss
                    if trade.stop_loss:
                        if trade.direction == "long" and price <= trade.stop_loss:
                            status = "sl_hit"
                            exit_price = trade.stop_loss
                            pnl = trade.quantity * (exit_price - trade.entry_price)
                            exit_time = datetime.now(timezone.utc)
                        elif trade.direction == "short" and price >= trade.stop_loss:
                            status = "sl_hit"
                            exit_price = trade.stop_loss
                            pnl = trade.quantity * (trade.entry_price - exit_price)
                            exit_time = datetime.now(timezone.utc)

                    # Check take profit
                    if status == "open" and trade.take_profit:
                        if trade.direction == "long" and price >= trade.take_profit:
                            status = "tp_hit"
                            exit_price = trade.take_profit
                            pnl = trade.quantity * (exit_price - trade.entry_price)
                            exit_time = datetime.now(timezone.utc)
                        elif trade.direction == "short" and price <= trade.take_profit:
                            status = "tp_hit"
                            exit_price = trade.take_profit
                            pnl = trade.quantity * (trade.entry_price - exit_price)
                            exit_time = datetime.now(timezone.utc)

                    # Check take profit 2
                    if status == "open" and trade.take_profit_2:
                        if trade.direction == "long" and price >= trade.take_profit_2:
                            status = "tp_hit"
                            exit_price = trade.take_profit_2
                            pnl = trade.quantity * (exit_price - trade.entry_price)
                            exit_time = datetime.now(timezone.utc)
                        elif trade.direction == "short" and price <= trade.take_profit_2:
                            status = "tp_hit"
                            exit_price = trade.take_profit_2
                            pnl = trade.quantity * (trade.entry_price - exit_price)
                            exit_time = datetime.now(timezone.utc)

                    if status != "open":
                        trade.status = status
                        trade.exit_price = exit_price
                        trade.exit_time = exit_time
                        pnl_pct = (pnl / (trade.entry_price * trade.quantity)) * 100 if trade.quantity * trade.entry_price else 0
                        trade.pnl = round(pnl, 2)
                        trade.pnl_pct = round(pnl_pct, 2)
                        db.commit()
                        logger.info(f"Trade #{trade.id} closed: {status}, P&L: ${pnl:.2f}")

                    checked += 1

                except Exception as e:
                    logger.error(f"Failed to check trade #{trade.id}: {e}")

    except Exception as e:
        logger.error(f"Database error during trade check: {e}")

    logger.info(f"Trade check complete: {checked} trades evaluated")
    return {"status": "ok", "checked": checked}
