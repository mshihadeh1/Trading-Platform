"""Signals API — list and trigger analysis."""

import json
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from app.database import get_db
from app.models.signal import Signal, SignalResponse, SignalResponseWithSymbol
from app.models.symbol import Symbol

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("", response_model=List[SignalResponseWithSymbol])
async def get_signals(
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """Get recent AI signals."""
    stmt = (
        select(Signal, Symbol)
        .outerjoin(Symbol, Signal.symbol_id == Symbol.symbol_id)
        .order_by(Signal.timestamp.desc())
        .limit(limit)
    )
    results = db.exec(stmt).all()

    signals = []
    for signal, symbol in results:
        resp = SignalResponseWithSymbol.model_validate(signal)
        if symbol:
            resp.display_name = symbol.display_name
        signals.append(resp)
    return signals


@router.get("/{signal_id}", response_model=SignalResponseWithSymbol)
async def get_signal(signal_id: int, db: Session = Depends(get_db)):
    """Get a single signal by ID."""
    signal = db.get(Signal, signal_id)
    if not signal:
        raise HTTPException(status_code=404, detail="Signal not found")

    resp = SignalResponseWithSymbol.model_validate(signal)
    return resp


@router.get("/latest")
async def get_latest_signal(
    symbol: str = Query(..., description="Symbol ticker"),
    db: Session = Depends(get_db),
):
    """Get the latest signal for a given symbol."""
    stmt = (
        select(Signal)
        .where(Signal.symbol == symbol)
        .order_by(Signal.timestamp.desc())
        .limit(1)
    )
    signal = db.exec(stmt).first()
    if not signal:
        return None
    return SignalResponse.model_validate(signal)


@router.post("/analyze/{symbol}")
async def trigger_analysis(
    symbol: str,
    db: Session = Depends(get_db),
):
    """Trigger a one-off AI analysis for a symbol."""
    # Find the symbol
    sym = db.exec(select(Symbol).where(Symbol.symbol == symbol)).first()
    if not sym:
        raise HTTPException(status_code=404, detail=f"Symbol '{symbol}' not found")

    # Trigger Celery task
    from app.worker.tasks import analyze_symbol_task
    task = analyze_symbol_task.delay(sym.symbol_id, sym.symbol, sym.exchange)
    return {"task_id": task.id}
