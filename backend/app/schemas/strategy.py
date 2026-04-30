from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel, ConfigDict, Field


class ConditionItem(BaseModel):
    indicator: str  # rsi, macd, bb_position, ema_alignment, volume_ratio, funding_rate, atr_pct
    operator: str  # lt, gt, lte, gte, crosses_above, crosses_below
    value: float


class StrategyCreate(BaseModel):
    name: str
    description: Optional[str] = None
    conditions: List[ConditionItem] = Field(default_factory=list)
    timeframe: str = "1h"
    exchange: str = "hyperliquid"


class StrategyUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    conditions: Optional[List[ConditionItem]] = None
    timeframe: Optional[str] = None
    exchange: Optional[str] = None
    is_active: Optional[bool] = None


class StrategyResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    conditions: List[dict[str, Any]] = Field(default_factory=list)
    timeframe: str
    exchange: str
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
