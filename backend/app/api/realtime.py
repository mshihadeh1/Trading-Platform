"""Lightweight WebSocket streams for live dashboard updates."""

import asyncio
from datetime import UTC, datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlmodel import Session, select

from app.database import engine
from app.models.candle import Candle
from app.models.paper_trade import PaperTrade
from app.models.signal import Signal
from app.models.symbol import Symbol

router = APIRouter()


def _snapshot() -> dict:
    with Session(engine) as db:
        latest_candle = db.exec(
            select(Candle, Symbol)
            .join(Symbol, Symbol.symbol_id == Candle.symbol_id)
            .order_by(Candle.timestamp.desc())
            .limit(1)
        ).first()
        latest_signal = db.exec(select(Signal).order_by(Signal.timestamp.desc()).limit(1)).first()
        open_trades = db.exec(select(PaperTrade).where(PaperTrade.status == "open")).all()

        candle_payload = None
        if latest_candle:
            candle, symbol = latest_candle
            candle_payload = {
                "symbol_id": symbol.symbol_id,
                "symbol": symbol.symbol,
                "exchange": symbol.exchange,
                "timestamp": candle.timestamp.isoformat() if candle.timestamp else None,
                "open": candle.open,
                "high": candle.high,
                "low": candle.low,
                "close": candle.close,
                "volume": candle.volume,
            }

        return {
            "type": "snapshot",
            "timestamp": datetime.now(UTC).isoformat(),
            "latest_candle": candle_payload,
            "latest_signal": {
                "id": latest_signal.id,
                "symbol": latest_signal.symbol,
                "direction": latest_signal.direction,
                "confidence": latest_signal.confidence,
                "timestamp": latest_signal.timestamp.isoformat() if latest_signal.timestamp else None,
            } if latest_signal else None,
            "open_positions": len(open_trades),
            "unrealized_pnl": round(sum(trade.pnl for trade in open_trades), 2),
        }


@router.websocket("/ws/stream")
async def realtime_stream(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            await websocket.send_json(_snapshot())
            await asyncio.sleep(5)
    except WebSocketDisconnect:
        return
