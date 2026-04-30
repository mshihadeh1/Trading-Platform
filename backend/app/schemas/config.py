from pydantic import BaseModel, ConfigDict
from typing import Optional


class AppConfigRequest(BaseModel):
    key: str
    value: str


class AppConfigResponse(BaseModel):
    id: int
    key: str
    value: str
    description: str
    updated_at: str

    model_config = ConfigDict(from_attributes=True)


class AppConfigUpdate(BaseModel):
    value: str
    description: Optional[str] = None
