from datetime import datetime
from app.utils.time import utc_now
from typing import Optional
from sqlmodel import Field, SQLModel, Column, String


class AppConfig(SQLModel, table=True):
    __tablename__ = "app_config"

    id: Optional[int] = Field(default=None, primary_key=True)
    key: str = Field(sa_column=Column(String(100), unique=True))
    value: str = "null"  # JSON string for complex values
    description: Optional[str] = None
    updated_at: datetime = Field(default_factory=utc_now)
