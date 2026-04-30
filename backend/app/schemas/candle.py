from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class CandleResponse(BaseModel):
    candle_id: int
    symbol_id: int
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float

    model_config = ConfigDict(from_attributes=True)


class CandleListResponse(BaseModel):
    candles: List[CandleResponse]
    symbol: str
    timeframe: str
