"""Strategy models."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, field_validator
from sqlmodel import JSON, SQLModel, Field


class Strategy(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    description: str = ""
    conditions: str = Field(default="[]", sa_column=JSON)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class StrategyCreate(BaseModel):
    name: str
    description: str = ""
    conditions: Optional[list] = None

    @field_validator("conditions", mode="before")
    @classmethod
    def validate_conditions(cls, v):
        if v is None:
            return "[]"
        return v


class StrategyUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    conditions: Optional[list] = None


class StrategyResponse(BaseModel):
    id: int
    name: str
    description: str
    conditions: list
