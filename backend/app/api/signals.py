"""Signals API — list and trigger analysis."""

import json
import logging
from typing import List, Optional

from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from app.database import get_db
from app.models.paper_trade import PaperTrade
from app.models.signal import Signal, SignalResponse, SignalResponseWithSymbol
from app.models.symbol import Symbol

router = APIRouter()
logger = logging.getLogger(__name__)


class ExecuteSignalRequest(BaseModel):
    quantity: float = 1.0
    notes: Optional[str] = None


def _signal_entry_price(signal: Signal) -> float | None:
    if signal.entry_price is not None:
        return signal.entry_price
    if signal.entry_min is not None and signal.entry_max is not None:
        return round((signal.entry_min + signal.entry_max) / 2, 8)
    return signal.entry_min or signal.entry_max


def _serialize_signal_trade(trade: PaperTrade, symbol: Symbol) -> dict:
    return {
        "id": trade.id,
        "symbol_id": trade.symbol_id,
        "symbol": symbol.symbol,
        "display_name": symbol.display_name,
        "direction": trade.direction,
        "entry_price": trade.entry_price,
        "quantity": trade.quantity,
        "current_price": trade.current_price,
        "stop_loss": trade.stop_loss,
        "take_profit": trade.take_profit,
        "take_profit_2": trade.take_profit_2,
        "status": trade.status,
        "exit_price": trade.exit_price,
        "pnl": trade.pnl,
        "pnl_pct": trade.pnl_pct,
        "entry_time": trade.entry_time,
        "exit_time": trade.exit_time,
        "source_signal_id": trade.source_signal_id,
        "close_reason": trade.close_reason,
        "notes": trade.notes,
    }


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


@router.post("/{signal_id}/execute", status_code=201)
async def execute_signal(
    signal_id: int,
    request: ExecuteSignalRequest | None = None,
    db: Session = Depends(get_db),
):
    """Create a paper trade from a buy/sell signal and link it back to the signal."""
    signal = db.get(Signal, signal_id)
    if not signal:
        raise HTTPException(status_code=404, detail="Signal not found")
    if signal.paper_trade_id is not None:
        existing = db.get(PaperTrade, signal.paper_trade_id)
        if existing:
            symbol = db.get(Symbol, existing.symbol_id)
            if symbol:
                return _serialize_signal_trade(existing, symbol)
    if signal.direction == "hold":
        raise HTTPException(status_code=400, detail="Hold signals cannot be executed as paper trades")
    if signal.direction not in {"buy", "sell"}:
        raise HTTPException(status_code=400, detail=f"Unsupported signal direction: {signal.direction}")
    if not signal.symbol_id:
        raise HTTPException(status_code=400, detail="Signal is not linked to a known symbol")

    symbol = db.get(Symbol, signal.symbol_id)
    if not symbol:
        raise HTTPException(status_code=404, detail="Signal symbol not found")

    quantity = request.quantity if request else 1.0
    if quantity <= 0:
        raise HTTPException(status_code=400, detail="Quantity must be positive")

    entry_price = _signal_entry_price(signal)
    if entry_price is None or entry_price <= 0:
        raise HTTPException(status_code=400, detail="Signal has no valid entry price")

    trade = PaperTrade(
        symbol_id=symbol.symbol_id,
        direction="long" if signal.direction == "buy" else "short",
        entry_price=entry_price,
        quantity=quantity,
        current_price=entry_price,
        stop_loss=signal.stop_loss,
        take_profit=signal.take_profit,
        take_profit_2=signal.take_profit_2,
        source_signal_id=signal.id,
        notes=(request.notes if request and request.notes else f"Executed from signal #{signal.id}: {signal.setup_type} {signal.time_horizon}"),
    )
    db.add(trade)
    db.commit()
    db.refresh(trade)
    signal.paper_trade_id = trade.id
    db.add(signal)
    db.commit()
    db.refresh(trade)
    return _serialize_signal_trade(trade, symbol)


@router.get("/{signal_id}", response_model=SignalResponseWithSymbol)
async def get_signal(signal_id: int, db: Session = Depends(get_db)):
    """Get a single signal by ID."""
    signal = db.get(Signal, signal_id)
    if not signal:
        raise HTTPException(status_code=404, detail="Signal not found")

    resp = SignalResponseWithSymbol.model_validate(signal)
    return resp


@router.post("/analyze/{symbol}")
async def trigger_analysis(
    symbol: str,
    db: Session = Depends(get_db),
):
    """Trigger a one-off AI analysis for a symbol (runs synchronously)."""
    sym = db.exec(select(Symbol).where(Symbol.symbol == symbol)).first()
    if not sym:
        raise HTTPException(status_code=404, detail=f"Symbol '{symbol}' not found")

    from app.services.llm_analysis import LLMAnalysisService

    service = LLMAnalysisService()
    signal = await service.analyze_and_store(db, sym)

    if not signal:
        raise HTTPException(status_code=500, detail=f"Analysis failed for {sym.symbol}")

    # Commit the signal
    db.commit()
    db.refresh(signal)

    return {
        "signal_id": signal.id,
        "symbol": sym.symbol,
        "direction": signal.direction,
        "confidence": signal.confidence,
        "setup_type": signal.setup_type,
    }
