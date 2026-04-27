"""Trade models."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel
from sqlmodel import SQLModel, Field


class Trade(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    symbol: str = Field(index=True)
    exchange: str
    side: str  # "buy" or "sell" (for paper trading)
    entry_price: float
    quantity: float = 1.0
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    exit_price: Optional[float] = None
    pnl: Optional[float] = None
    pnl_percent: Optional[float] = None
    status: str = "open"  # open, closed, cancelled
    trading_mode: str = "paper"  # paper or live
    close_reason: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    closed_at: Optional[datetime] = None
    current_price: Optional[float] = None


class TradeCreate(BaseModel):
    symbol: str
    exchange: str = "HYPERLIQUID"
    side: str
    quantity: float = 1.0
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None


class TradeResponse(BaseModel):
    id: int
    symbol: str
    exchange: str
    side: str
    entry_price: float
    quantity: float
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    exit_price: Optional[float] = None
    pnl: Optional[float] = None
    pnl_percent: Optional[float] = None
    status: str
    trading_mode: str
    created_at: str = ""
    closed_at: Optional[str] = None

