from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class SignalCreate(BaseModel):
    symbol_id: int
    direction: str
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    take_profit_2: Optional[float] = None
    confidence: int = 0
    reasoning: Optional[str] = None
    analysis_type: str = "ai"
    raw_response: Optional[str] = None


class SignalResponse(BaseModel):
    id: int
    symbol_id: int
    timestamp: datetime
    direction: str
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    take_profit_2: Optional[float] = None
    confidence: int
    reasoning: Optional[str] = None
    llm_model_used: Optional[str] = None
    analysis_type: str
    raw_response: Optional[str] = None

    class Config:
        from_attributes = True


class SignalResponseWithSymbol(SignalResponse):
    symbol: Optional[str] = None
    display_name: Optional[str] = None
    exchange: Optional[str] = None
