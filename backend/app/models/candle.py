from datetime import datetime
from typing import Optional, List
from sqlmodel import Field, SQLModel
from sqlalchemy import Index, Float


class Candle(SQLModel, table=True):
    __tablename__ = "candles"

    candle_id: Optional[int] = Field(default=None, primary_key=True)
    symbol_id: int = Field(foreign_key="symbols.symbol_id")
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float

    __table_args__ = (
        Index("idx_candle_symbol_time", "symbol_id", "timestamp"),
    )

    @property
    def symbol(self) -> "Symbol":
        from app.models.symbol import Symbol
        return Symbol(symbol_id=self.symbol_id)
