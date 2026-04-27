from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select, text
from app.database import get_db
from app.models.config import AppConfig
from app.schemas.config import AppConfigRequest, AppConfigResponse, AppConfigUpdate
from typing import List

router = APIRouter()


@router.get("", response_model=List[AppConfigResponse])
async def get_configs(db: Session = Depends(get_db)):
    stmt = select(AppConfig).order_by(AppConfig.key)
    return db.exec(stmt).all()


@router.get("/{key}", response_model=AppConfigResponse)
async def get_config(key: str, db: Session = Depends(get_db)):
    stmt = select(AppConfig).where(AppConfig.key == key)
    config = db.exec(stmt).first()
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")
    return config


@router.put("/{key}")
async def update_config(key: str, item: AppConfigUpdate, db: Session = Depends(get_db)):
    stmt = select(AppConfig).where(AppConfig.key == key)
    config = db.exec(stmt).first()
    if not config:
        config = AppConfig(key=key, value=item.value, description=item.description or "")
        db.add(config)
    else:
        config.value = item.value
        if item.description:
            config.description = item.description
        config.updated_at = db.func.now()
    db.commit()
    db.refresh(config)
    return config
