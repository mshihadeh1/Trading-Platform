"""Backtest schemas."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class BacktestRunRequest(BaseModel):
    strategy_id: int
    symbol_id: Optional[int] = None
    start_date: str  # ISO format
    end_date: str  # ISO format
    initial_capital: float = 10000.0
    fee_bps: float = 10.0
    slippage_bps: float = 5.0


class BacktestResponse(BaseModel):
    id: int
    strategy_id: int
    symbol_id: Optional[int] = None
    timeframe: str
    initial_capital: float
    fee_bps: float
    slippage_bps: float
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
    equity_curve: Optional[list[dict]] = None
    trade_log: Optional[list[dict]] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
