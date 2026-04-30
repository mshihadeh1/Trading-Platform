"""Daily brief API routes."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session

from app.database import get_db
from app.models.daily_brief import DailyBriefResponse
from app.services.daily_brief import DailyBriefService

router = APIRouter()


@router.get("/latest", response_model=DailyBriefResponse | None)
def latest_daily_brief(db: Session = Depends(get_db)):
    service = DailyBriefService()
    brief = service.latest(db)
    return service.to_response(brief) if brief else None


@router.get("/history", response_model=list[DailyBriefResponse])
def daily_brief_history(limit: int = Query(default=20, ge=1, le=100), db: Session = Depends(get_db)):
    service = DailyBriefService()
    return [service.to_response(brief) for brief in service.history(db, limit=limit)]


@router.post("/generate", response_model=DailyBriefResponse, status_code=status.HTTP_201_CREATED)
def generate_daily_brief(db: Session = Depends(get_db)):
    service = DailyBriefService()
    try:
        brief = service.generate(db)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to generate daily brief: {exc}") from exc
    return service.to_response(brief)
