from datetime import datetime
from app.utils.time import utc_now
from typing import Optional
from sqlmodel import Field, SQLModel
from sqlalchemy import Index


class Symbol(SQLModel, table=True):
    __tablename__ = "symbols"

    symbol_id: Optional[int] = Field(default=None, primary_key=True)
    exchange: str  # "hyperliquid" or "yahoo"
    symbol_type: str  # "perp" or "stock" or "crypto" or "etf"
    symbol: str  # e.g. "BTC", "AAPL"
    display_name: str  # e.g. "BTC-PERP", "Apple Inc."
    added_at: datetime = Field(default_factory=utc_now)
    is_active: bool = True

    __table_args__ = (
        Index("idx_symbol_exchange", "exchange", "symbol"),
    )
