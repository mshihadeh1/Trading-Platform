"""Backtest schemas."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class BacktestRunRequest(BaseModel):
    strategy_id: int
    start_date: str  # ISO format
    end_date: str  # ISO format
    initial_capital: float = 10000.0


class BacktestResponse(BaseModel):
    id: int
    strategy_id: int
    start_date: datetime
    end_date: datetime
    win_rate: float
    profit_factor: float
    max_drawdown: float
    total_return: float
    sharpe_ratio: float
    sortino_ratio: float
    trades_count: int
    avg_trade_duration_hours: float
    avg_win: float
    avg_loss: float
    equity_curve: Optional[str] = None
    trade_log: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
