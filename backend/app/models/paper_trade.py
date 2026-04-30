from datetime import datetime
from app.utils.time import utc_now
from typing import Optional
from sqlmodel import Field, SQLModel


class PaperTrade(SQLModel, table=True):
    __tablename__ = "paper_trades"

    id: Optional[int] = Field(default=None, primary_key=True)
    symbol_id: int = Field(foreign_key="symbols.symbol_id")
    direction: str  # "long" or "short"
    entry_price: float
    quantity: float = 1.0
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    take_profit_2: Optional[float] = None
    status: str = "open"  # "open", "closed", "sl_hit", "tp_hit"
    exit_price: Optional[float] = None
    pnl: float = 0.0
    pnl_pct: float = 0.0
    current_price: Optional[float] = None
    entry_time: datetime = Field(default_factory=utc_now)
    exit_time: Optional[datetime] = None
    strategy_id: Optional[int] = Field(default=None, foreign_key="strategies.id")
    source_signal_id: Optional[int] = Field(default=None, foreign_key="signals.id")
    close_reason: Optional[str] = None
    notes: Optional[str] = None
