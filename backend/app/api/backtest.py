"""Backtest API — run and retrieve backtest results."""

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from datetime import datetime

from app.database import get_db
from app.models.backtest_result import BacktestResult
from app.schemas.backtest_result import BacktestRunRequest, BacktestMetrics, BacktestResponse
from app.worker.tasks import fetch_historical_data, analyze_all_signals

router = APIRouter()


@router.get("", response_model=list[BacktestResponse])
async def get_backtests(
    db: Session = Depends(get_db),
    strategy_id: int = None,
    limit: int = 20,
):
    """List backtest results."""
    stmt = select(BacktestResult)
    if strategy_id:
        stmt = stmt.where(BacktestResult.strategy_id == strategy_id)
    stmt = stmt.order_by(BacktestResult.created_at.desc()).limit(limit)
    results = db.exec(stmt).all()
    return results


@router.post("/run", response_model=BacktestResponse, status_code=201)
async def run_backtest(item: BacktestRunRequest, db: Session = Depends(get_db)):
    """Run a backtest for a strategy."""
    # Get the strategy to extract conditions
    from app.models.strategy import Strategy
    strategy = db.get(Strategy, item.strategy_id)
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")

    # Load historical data first (trigger Celery task)
    fetch_historical_data.delay()

    # Create backtest result (placeholder until engine is fully built)
    result = BacktestResult(
        strategy_id=item.strategy_id,
        start_date=item.start_date,
        end_date=item.end_date,
        win_rate=0.0,
        profit_factor=0.0,
        max_drawdown=0.0,
        total_return=0.0,
        sharpe_ratio=0.0,
        sortino_ratio=0.0,
        trades_count=0,
        avg_trade_duration_hours=0.0,
        avg_win=0.0,
        avg_loss=0.0,
    )
    db.add(result)
    db.commit()
    db.refresh(result)
    return result
