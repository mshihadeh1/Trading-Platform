from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import List
from datetime import datetime
from app.utils.time import utc_now
from app.database import get_db
from app.models.strategy import Strategy
from app.schemas.strategy import StrategyCreate, StrategyUpdate, StrategyResponse

router = APIRouter()


@router.get("", response_model=List[StrategyResponse])
async def get_strategies(db: Session = Depends(get_db)):
    stmt = select(Strategy).where(Strategy.is_active == True).order_by(Strategy.created_at.desc())
    return db.exec(stmt).all()


@router.post("", response_model=StrategyResponse, status_code=201)
async def create_strategy(item: StrategyCreate, db: Session = Depends(get_db)):
    strategy = Strategy(
        name=item.name,
        description=item.description or "",
        conditions=[c.model_dump() for c in item.conditions],
        timeframe=item.timeframe,
        exchange=item.exchange,
    )
    db.add(strategy)
    db.commit()
    db.refresh(strategy)
    return strategy


@router.put("/{strategy_id}")
async def update_strategy(strategy_id: int, item: StrategyUpdate, db: Session = Depends(get_db)):
    strategy = db.get(Strategy, strategy_id)
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")

    for key, value in item.model_dump(exclude_unset=True).items():
        if key == "conditions" and value:
            value = [c.model_dump() for c in value]
        setattr(strategy, key, value)

    strategy.updated_at = utc_now()
    db.commit()
    db.refresh(strategy)
    return strategy


@router.delete("/{strategy_id}")
async def delete_strategy(strategy_id: int, db: Session = Depends(get_db)):
    strategy = db.get(Strategy, strategy_id)
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")
    strategy.is_active = False
    strategy.updated_at = utc_now()
    db.commit()
    return {"message": "Strategy deactivated"}
