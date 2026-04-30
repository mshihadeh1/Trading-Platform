from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class SymbolCreate(BaseModel):
    exchange: str
    symbol_type: str = "perp"
    symbol: str
    display_name: Optional[str] = None


class SymbolUpdate(BaseModel):
    symbol: Optional[str] = None
    display_name: Optional[str] = None
    is_active: Optional[bool] = None


class SymbolResponse(BaseModel):
    symbol_id: int
    exchange: str
    symbol_type: str
    symbol: str
    display_name: str
    added_at: datetime
    is_active: bool

    model_config = ConfigDict(from_attributes=True)
