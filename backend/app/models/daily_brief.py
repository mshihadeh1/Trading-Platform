"""Daily brief model."""

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field as PydanticField, field_validator
from sqlmodel import Field, SQLModel

from app.utils.time import utc_now


class DailyBrief(SQLModel, table=True):
    """Persisted daily market preparation brief."""

    __tablename__ = "daily_briefs"

    id: Optional[int] = Field(default=None, primary_key=True)
    brief_date: date = Field(index=True)
    market_regime: str = "mixed"
    summary: str = ""
    top_opportunities_json: str = "[]"
    risk_notes: str = ""
    open_positions_summary_json: str = "{}"
    watchlist_snapshot_json: str = "[]"
    llm_reasoning: str = ""
    created_at: datetime = Field(default_factory=utc_now, index=True)


class DailyBriefResponse(BaseModel):
    """API response for a daily brief."""

    id: int
    brief_date: date
    market_regime: str
    summary: str
    top_opportunities: list[dict] = PydanticField(default_factory=list)
    risk_notes: str
    open_positions_summary: dict = PydanticField(default_factory=dict)
    watchlist_snapshot: list[dict] = PydanticField(default_factory=list)
    llm_reasoning: str
    created_at: datetime

    @field_validator("market_regime")
    @classmethod
    def normalize_market_regime(cls, value: str) -> str:
        value = str(value or "mixed").strip().lower()
        return value if value in {"bullish", "bearish", "choppy", "risk-off", "risk-on", "mixed"} else "mixed"

    model_config = ConfigDict(from_attributes=True)
