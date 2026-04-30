"""Signal models."""

from datetime import datetime
from app.utils.time import utc_now
from typing import Optional

from pydantic import BaseModel, ConfigDict
from sqlmodel import SQLModel, Field


class Signal(SQLModel, table=True):
    """AI-generated trading signal stored in DB."""
    __tablename__ = "signals"

    id: Optional[int] = Field(default=None, primary_key=True)
    symbol_id: Optional[int] = Field(default=None, foreign_key="symbols.symbol_id")
    symbol: str = Field(index=True)
    exchange: str = "hyperliquid"
    direction: str = "hold"  # buy, sell, hold
    entry_price: Optional[float] = None
    entry_min: Optional[float] = None
    entry_max: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    take_profit_2: Optional[float] = None
    confidence: int = 50
    setup_type: str = "unspecified"
    time_horizon: str = "swing"
    risk_reward: Optional[float] = None
    invalidation: str = ""
    reasoning: str = ""
    indicators_data: Optional[str] = None
    llm_model: Optional[str] = None
    analysis_type: str = "ai"
    raw_response: Optional[str] = None
    paper_trade_id: Optional[int] = Field(default=None, foreign_key="paper_trades.id")
    timestamp: Optional[datetime] = Field(default_factory=utc_now)


class SignalCreate(BaseModel):
    """Pydantic schema for creating a signal via API."""
    symbol: str
    exchange: str = "hyperliquid"
    direction: str
    entry_price: Optional[float] = None
    entry_min: Optional[float] = None
    entry_max: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    take_profit_2: Optional[float] = None
    confidence: int = 50
    setup_type: str = "unspecified"
    time_horizon: str = "swing"
    risk_reward: Optional[float] = None
    invalidation: str = ""
    reasoning: str = ""


class SignalResponse(BaseModel):
    """Pydantic schema for signal responses."""
    id: int
    symbol_id: Optional[int] = None
    symbol: str
    exchange: str
    direction: str
    entry_price: Optional[float] = None
    entry_min: Optional[float] = None
    entry_max: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    take_profit_2: Optional[float] = None
    confidence: int
    setup_type: str = "unspecified"
    time_horizon: str = "swing"
    risk_reward: Optional[float] = None
    invalidation: str = ""
    reasoning: str
    indicators_data: Optional[str] = None
    llm_model: Optional[str] = None
    analysis_type: str
    raw_response: Optional[str] = None
    paper_trade_id: Optional[int] = None
    timestamp: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class SignalResponseWithSymbol(SignalResponse):
    """Signal response with symbol metadata."""
    display_name: Optional[str] = None
