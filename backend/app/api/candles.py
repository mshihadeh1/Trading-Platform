from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select
from typing import List
from app.database import get_db
from app.models.candle import Candle
from app.models.symbol import Symbol
from app.schemas.candle import CandleResponse, CandleListResponse
from app.services.candle_collector import CandleCollector

router = APIRouter()


@router.get("/{symbol_id}", response_model=CandleListResponse)
async def get_candles(symbol_id: int, db: Session = Depends(get_db),
                      limit: int = Query(default=100, le=500),
                      timeframe: str = Query(default="1h")):
    symbol = db.get(Symbol, symbol_id)
    if not symbol:
        raise HTTPException(status_code=404, detail="Symbol not found")

    stmt = (
        select(Candle)
        .where(Candle.symbol_id == symbol_id)
        .order_by(Candle.timestamp.desc())
        .limit(limit)
    )
    candles = db.exec(stmt).all()

    # Reverse to get chronological order
    candles.reverse()

    return CandleListResponse(
        candles=candles,
        symbol=symbol.display_name,
        timeframe=timeframe
    )


@router.post("/fetch/{symbol_id}")
async def fetch_candles(
    symbol_id: int,
    timeframe: str = Query(default="1h"),
    db: Session = Depends(get_db)
):
    """
    Fetch and store candles for a specific symbol.
    Triggers data collection from the appropriate exchange.
    """
    symbol = db.get(Symbol, symbol_id)
    if not symbol:
        raise HTTPException(status_code=404, detail="Symbol not found")

    collector = CandleCollector(db=db)
    
    try:
        if symbol.exchange == "hyperliquid":
            count = await collector.collect_symbol(
                symbol=symbol.symbol,
                exchange="hyperliquid",
                interval=timeframe,
                db=db
            )
        elif symbol.exchange == "yahoo":
            count = collector.collect_symbol(
                symbol=symbol.symbol,
                exchange="yahoo",
                interval=timeframe,
                db=db
            )
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported exchange: {symbol.exchange}"
            )

        return {
            "message": f"Fetched {count} candles for {symbol.symbol}",
            "symbol": symbol.symbol,
            "exchange": symbol.exchange,
            "candles_stored": count,
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/fetch/all")
async def fetch_all_candles(
    timeframe: str = Query(default="1h"),
    db: Session = Depends(get_db)
):
    """
    Fetch and store candles for all symbols in the watchlist.
    """
    collector = CandleCollector(db=db)
    
    try:
        # Fetch from Hyperliquid
        hl_results = await collector.collect_all_hyperliquid(db=db)
        
        # Fetch from Yahoo Finance
        yf_results = collector.collect_all_yahoo(db=db)
        
        total_stored = sum(hl_results.values()) + sum(yf_results.values())
        
        return {
            "message": f"Fetched candles for {len(hl_results) + len(yf_results)} symbols",
            "hyperliquid": hl_results,
            "yahoo_finance": yf_results,
            "total_candles_stored": total_stored,
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
