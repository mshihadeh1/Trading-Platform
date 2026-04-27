from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import List
from app.database import get_db
from app.models.paper_trade import PaperTrade
from app.models.symbol import Symbol
from app.schemas.paper_trade import PaperTradeCreate, PaperTradeResponse, PortfolioSummary
from app.config import settings

router = APIRouter()


@router.get("/summary", response_model=PortfolioSummary)
async def get_portfolio_summary(db: Session = Depends(get_db)):
    """Get paper trading portfolio summary."""
    trades = db.exec(select(PaperTrade)).all()

    open_trades = [t for t in trades if t.status == "open"]
    closed_trades = [t for t in trades if t.status != "open"]

    realized_pnl = sum(t.pnl for t in closed_trades)
    total_pnl = realized_pnl + sum(t.pnl for t in open_trades)

    wins = len([t for t in closed_trades if t.pnl > 0])
    win_rate = (wins / len(closed_trades) * 100) if closed_trades else 0.0

    current_equity = settings.initial_capital + total_pnl

    return PortfolioSummary(
        total_pnl=total_pnl,
        total_pnl_pct=(total_pnl / settings.initial_capital * 100) if settings.initial_capital else 0,
        realized_pnl=realized_pnl,
        unrealized_pnl=sum(t.pnl for t in open_trades),
        open_positions=len(open_trades),
        total_trades=len(closed_trades),
        win_rate=win_rate,
        current_equity=current_equity,
    )


@router.get("", response_model=List[PaperTradeResponse])
async def get_trades(db: Session = Depends(get_db)):
    stmt = select(PaperTrade).order_by(PaperTrade.entry_time.desc())
    return db.exec(stmt).all()


@router.post("", response_model=PaperTradeResponse, status_code=201)
async def create_trade(item: PaperTradeCreate, db: Session = Depends(get_db)):
    trade = PaperTrade(**item.model_dump())
    db.add(trade)
    db.commit()
    db.refresh(trade)
    return trade
