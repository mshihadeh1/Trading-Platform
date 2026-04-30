from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class PaperTradeCreate(BaseModel):
    symbol_id: int
    direction: str = "long"
    entry_price: float
    quantity: float = 1.0
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    take_profit_2: Optional[float] = None
    notes: Optional[str] = None


class PaperTradeResponse(BaseModel):
    id: int
    symbol_id: int
    direction: str
    entry_price: float
    quantity: float
    current_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    take_profit_2: Optional[float] = None
    status: str
    exit_price: Optional[float] = None
    pnl: float
    pnl_pct: float
    entry_time: datetime
    exit_time: Optional[datetime] = None
    strategy_id: Optional[int] = None
    source_signal_id: Optional[int] = None
    close_reason: Optional[str] = None
    notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class PortfolioSummary(BaseModel):
    total_pnl: float
    total_pnl_pct: float
    realized_pnl: float
    unrealized_pnl: float
    open_positions: int
    total_trades: int
    win_rate: float
    current_equity: float
