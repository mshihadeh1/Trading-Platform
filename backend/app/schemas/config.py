from pydantic import BaseModel


class AppConfigRequest(BaseModel):
    key: str
    value: str


class AppConfigResponse(BaseModel):
    id: int
    key: str
    value: str
    description: str
    updated_at: str

    class Config:
        from_attributes = True


class AppConfigUpdate(BaseModel):
    value: str
    description: Optional[str] = None
