from datetime import datetime
from typing import Optional
from sqlmodel import Field, SQLModel


class BacktestResult(SQLModel, table=True):
    __tablename__ = "backtest_results"

    id: Optional[int] = Field(default=None, primary_key=True)
    strategy_id: int = Field(foreign_key="strategies.id")
    start_date: datetime
    end_date: datetime
    win_rate: float = 0.0
    profit_factor: float = 0.0
    max_drawdown: float = 0.0
    total_return: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    trades_count: int = 0
    avg_trade_duration_hours: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    equity_curve: Optional[str] = None  # JSON string
    trade_log: Optional[str] = None  # JSON string
    created_at: datetime = Field(default_factory=datetime.utcnow)
