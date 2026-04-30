"""Strategy models."""

from datetime import datetime
from app.utils.time import utc_now
from typing import Any, Optional

from sqlmodel import JSON, Field, SQLModel


class Strategy(SQLModel, table=True):
    __tablename__ = "strategies"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    description: str = ""
    conditions: list[dict[str, Any]] = Field(default_factory=list, sa_type=JSON)
    timeframe: str = "1h"
    exchange: str = "hyperliquid"
    is_active: bool = True
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: Optional[datetime] = Field(default_factory=utc_now)
