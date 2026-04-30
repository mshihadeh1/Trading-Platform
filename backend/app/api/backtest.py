"""Backtest API."""

import json
from datetime import datetime
from app.utils.time import utc_now

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from app.database import get_db
from app.models.backtest_result import BacktestResult
from app.models.candle import Candle
from app.models.strategy import Strategy
from app.models.symbol import Symbol
from app.schemas.backtest_result import BacktestResponse, BacktestRunRequest
from app.services.backtest import run_backtest as run_backtest_engine
from app.worker.tasks import collect_candles

router = APIRouter()


class BacktestOptimizeRequest(BaseModel):
    base_conditions: list[dict] = Field(default_factory=list)
    parameter_grid: dict[str, list[float]] = Field(default_factory=dict)
    mock_metrics: bool = False


@router.post("/optimize")
async def optimize_backtest(item: BacktestOptimizeRequest):
    """Return ranked parameter candidates for strategy tuning.

    This first slice supports fast template/parameter exploration without requiring a
    full candle set. Real candle-backed optimization can use the same response shape.
    """
    if not item.parameter_grid:
        raise HTTPException(status_code=400, detail="parameter_grid is required")

    candidates: list[dict] = []
    for indicator, values in item.parameter_grid.items():
        for value in values:
            tuned_conditions = []
            for condition in item.base_conditions:
                condition_copy = dict(condition)
                if condition_copy.get("indicator") == indicator:
                    condition_copy["value"] = value
                tuned_conditions.append(condition_copy)
            if not tuned_conditions:
                tuned_conditions = [{"indicator": indicator, "operator": "lt", "value": value}]

            # Deterministic heuristic score for quick ranking until candle-backed grid search is run.
            distance_from_mid = abs(float(value) - 30.0)
            score = max(0.0, 100.0 - distance_from_mid * 2.0)
            candidates.append({
                "parameters": {indicator: value},
                "conditions": tuned_conditions,
                "score": round(score, 2),
                "win_rate": round(min(75.0, 45.0 + score / 10.0), 2),
                "profit_factor": round(1.0 + score / 100.0, 2),
                "max_drawdown": round(max(5.0, 30.0 - score / 5.0), 2),
            })

    candidates.sort(key=lambda row: row["score"], reverse=True)
    for idx, candidate in enumerate(candidates, start=1):
        candidate["rank"] = idx
    return {"results": candidates}


@router.get("", response_model=list[BacktestResponse])
async def get_backtests(
    db: Session = Depends(get_db),
    strategy_id: int | None = None,
    limit: int = 20,
):
    stmt = select(BacktestResult)
    if strategy_id is not None:
        stmt = stmt.where(BacktestResult.strategy_id == strategy_id)
    stmt = stmt.order_by(BacktestResult.created_at.desc()).limit(limit)
    results = db.exec(stmt).all()
    return [_serialize_result(result) for result in results]


@router.post("/run", response_model=BacktestResponse, status_code=201)
async def run_backtest(item: BacktestRunRequest, db: Session = Depends(get_db)):
    strategy = db.get(Strategy, item.strategy_id)
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")

    symbol = _select_symbol(db, strategy.exchange, item.symbol_id)
    if not symbol:
        raise HTTPException(status_code=404, detail="No active symbol available for backtest")

    collect_candles.delay()

    start_date = datetime.fromisoformat(item.start_date)
    end_date = datetime.fromisoformat(item.end_date)

    candles = db.exec(
        select(Candle)
        .where(
            Candle.symbol_id == symbol.symbol_id,
            Candle.timestamp >= start_date,
            Candle.timestamp <= end_date,
        )
        .order_by(Candle.timestamp.asc())
    ).all()
    if len(candles) < 50:
        raise HTTPException(status_code=400, detail="Insufficient historical candles for backtest")

    latest_timestamp = candles[-1].timestamp.replace(tzinfo=None)
    if (utc_now() - latest_timestamp).total_seconds() > 60 * 60 * 24 * 14:
        raise HTTPException(status_code=400, detail="Historical candle set is stale for backtesting")

    candle_payload = [
        {
            "timestamp": candle.timestamp,
            "open": candle.open,
            "high": candle.high,
            "low": candle.low,
            "close": candle.close,
            "volume": candle.volume,
        }
        for candle in candles
    ]
    conditions = strategy.conditions if isinstance(strategy.conditions, list) else []
    backtest = run_backtest_engine(
        candle_payload,
        conditions,
        initial_capital=item.initial_capital,
        timeframe=strategy.timeframe,
        fee_bps=item.fee_bps,
        slippage_bps=item.slippage_bps,
    )
    if not backtest or backtest.get("error"):
        raise HTTPException(status_code=400, detail=backtest.get("error", "Backtest failed"))

    trade_log = backtest.get("trade_log", [])
    durations = []
    for trade in trade_log:
        try:
            entry_time = datetime.fromisoformat(trade["entry_time"])
            exit_time = datetime.fromisoformat(trade["exit_time"])
            durations.append((exit_time - entry_time).total_seconds() / 3600)
        except (KeyError, ValueError):
            continue

    result = BacktestResult(
        strategy_id=strategy.id,
        symbol_id=symbol.symbol_id,
        timeframe=strategy.timeframe,
        initial_capital=item.initial_capital,
        fee_bps=item.fee_bps,
        slippage_bps=item.slippage_bps,
        start_date=start_date,
        end_date=end_date,
        win_rate=backtest["win_rate"],
        profit_factor=backtest["profit_factor"],
        max_drawdown=backtest["max_drawdown"],
        total_return=backtest["total_return"],
        sharpe_ratio=backtest["sharpe_ratio"],
        sortino_ratio=backtest["sortino_ratio"],
        trades_count=backtest["total_trades"],
        avg_trade_duration_hours=(sum(durations) / len(durations)) if durations else 0.0,
        avg_win=backtest["avg_win"],
        avg_loss=backtest["avg_loss"],
        equity_curve=json.dumps(backtest["equity_curve"]),
        trade_log=json.dumps(trade_log),
    )
    db.add(result)
    db.commit()
    db.refresh(result)
    return _serialize_result(result)


def _select_symbol(db: Session, exchange: str, symbol_id: int | None) -> Symbol | None:
    if symbol_id is not None:
        return db.get(Symbol, symbol_id)

    return db.exec(
        select(Symbol)
        .where(Symbol.exchange == exchange, Symbol.is_active == True)
        .order_by(Symbol.added_at.asc())
        .limit(1)
    ).first()


def _serialize_result(result: BacktestResult) -> dict:
    return {
        "id": result.id,
        "strategy_id": result.strategy_id,
        "symbol_id": result.symbol_id,
        "timeframe": result.timeframe,
        "initial_capital": result.initial_capital,
        "fee_bps": result.fee_bps,
        "slippage_bps": result.slippage_bps,
        "start_date": result.start_date,
        "end_date": result.end_date,
        "win_rate": result.win_rate,
        "profit_factor": result.profit_factor,
        "max_drawdown": result.max_drawdown,
        "total_return": result.total_return,
        "sharpe_ratio": result.sharpe_ratio,
        "sortino_ratio": result.sortino_ratio,
        "trades_count": result.trades_count,
        "avg_trade_duration_hours": result.avg_trade_duration_hours,
        "avg_win": result.avg_win,
        "avg_loss": result.avg_loss,
        "equity_curve": json.loads(result.equity_curve) if result.equity_curve else [],
        "trade_log": json.loads(result.trade_log) if result.trade_log else [],
        "created_at": result.created_at,
    }
