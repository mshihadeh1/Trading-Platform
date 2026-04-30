"""Asset watchlist models."""

from datetime import datetime
from app.utils.time import utc_now
from typing import Optional

from pydantic import BaseModel
from sqlmodel import SQLModel, Field


class Asset(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    symbol: str = Field(index=True)
    name: str
    exchange: str = "HYPERLIQUID"
    asset_type: str = "crypto"
    active: bool = True
    created_at: datetime = Field(default_factory=utc_now)


class AssetCreate(BaseModel):
    symbol: str
    name: Optional[str] = None
    exchange: Optional[str] = "HYPERLIQUID"
    asset_type: Optional[str] = "crypto"


class AssetUpdate(BaseModel):
    active: Optional[bool] = None


class AssetResponse(BaseModel):
    id: int
    symbol: str
    name: str
    exchange: str
    asset_type: str
    active: bool
