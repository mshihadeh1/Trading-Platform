from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import List
from app.database import get_db
from app.models.symbol import Symbol
from app.schemas.symbol import SymbolCreate, SymbolUpdate, SymbolResponse
from datetime import datetime

router = APIRouter()


@router.get("", response_model=List[SymbolResponse])
async def get_watchlist(db: Session = Depends(get_db)):
    stmt = select(Symbol).where(Symbol.is_active == True).order_by(Symbol.added_at)
    symbols = db.exec(stmt).all()
    return symbols


@router.post("", response_model=SymbolResponse, status_code=201)
async def add_symbol(item: SymbolCreate, db: Session = Depends(get_db)):
    # Check if symbol already exists
    stmt = select(Symbol).where(Symbol.exchange == item.exchange, Symbol.symbol == item.symbol)
    existing = db.exec(stmt).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Symbol {item.symbol} already exists on {item.exchange}")

    symbol = Symbol(**item.model_dump())
    db.add(symbol)
    db.commit()
    db.refresh(symbol)
    return symbol


@router.delete("/{symbol_id}")
async def remove_symbol(symbol_id: int, db: Session = Depends(get_db)):
    symbol = db.get(Symbol, symbol_id)
    if not symbol:
        raise HTTPException(status_code=404, detail="Symbol not found")
    symbol.is_active = False
    db.commit()
    return {"message": "Symbol removed"}


@router.post("/seed")
async def seed_symbols(db: Session = Depends(get_db)):
    """
    Seed the database with default symbols from Hyperliquid and Yahoo Finance.
    Creates symbols that don't already exist.
    """
    hyperliquid_symbols = [
        {"symbol": "BTC", "display_name": "BTC-PERP", "symbol_type": "perp"},
        {"symbol": "ETH", "display_name": "ETH-PERP", "symbol_type": "perp"},
        {"symbol": "SOL", "display_name": "SOL-PERP", "symbol_type": "perp"},
        {"symbol": "BNB", "display_name": "BNB-PERP", "symbol_type": "perp"},
        {"symbol": "XRP", "display_name": "XRP-PERP", "symbol_type": "perp"},
        {"symbol": "DOGE", "display_name": "DOGE-PERP", "symbol_type": "perp"},
        {"symbol": "AVAX", "display_name": "AVAX-PERP", "symbol_type": "perp"},
        {"symbol": "ARB", "display_name": "ARB-PERP", "symbol_type": "perp"},
        {"symbol": "OP", "display_name": "OP-PERP", "symbol_type": "perp"},
        {"symbol": "WIF", "display_name": "WIF-PERP", "symbol_type": "perp"},
        {"symbol": "PEPE", "display_name": "PEPE-PERP", "symbol_type": "perp"},
        {"symbol": "SUI", "display_name": "SUI-PERP", "symbol_type": "perp"},
        {"symbol": "LINK", "display_name": "LINK-PERP", "symbol_type": "perp"},
        {"symbol": "AAVE", "display_name": "AAVE-PERP", "symbol_type": "perp"},
        {"symbol": "FET", "display_name": "FET-PERP", "symbol_type": "perp"},
    ]

    yahoo_symbols = [
        {"symbol": "SPY", "display_name": "S&P 500 ETF", "symbol_type": "etf"},
        {"symbol": "QQQ", "display_name": "Nasdaq 100 ETF", "symbol_type": "etf"},
        {"symbol": "AAPL", "display_name": "Apple Inc.", "symbol_type": "stock"},
        {"symbol": "TSLA", "display_name": "Tesla Inc.", "symbol_type": "stock"},
        {"symbol": "NVDA", "display_name": "NVIDIA Corp.", "symbol_type": "stock"},
        {"symbol": "MSFT", "display_name": "Microsoft Corp.", "symbol_type": "stock"},
        {"symbol": "AMZN", "display_name": "Amazon.com Inc.", "symbol_type": "stock"},
        {"symbol": "META", "display_name": "Meta Platforms", "symbol_type": "stock"},
        {"symbol": "GOOGL", "display_name": "Alphabet Inc.", "symbol_type": "stock"},
        {"symbol": "BTC-USD", "display_name": "Bitcoin USD", "symbol_type": "crypto"},
        {"symbol": "ETH-USD", "display_name": "Ethereum USD", "symbol_type": "crypto"},
    ]

    created = []
    skipped = []

    # Seed Hyperliquid symbols
    for sym_data in hyperliquid_symbols:
        existing = db.exec(
            select(Symbol).where(
                Symbol.exchange == "hyperliquid",
                Symbol.symbol == sym_data["symbol"]
            )
        ).first()

        if existing:
            skipped.append(sym_data["symbol"])
            continue

        new_symbol = Symbol(
            exchange="hyperliquid",
            symbol_type=sym_data["symbol_type"],
            symbol=sym_data["symbol"],
            display_name=sym_data["display_name"],
            is_active=True,
        )
        db.add(new_symbol)
        created.append(sym_data["symbol"])

    # Seed Yahoo Finance symbols
    for sym_data in yahoo_symbols:
        existing = db.exec(
            select(Symbol).where(
                Symbol.exchange == "yahoo",
                Symbol.symbol == sym_data["symbol"]
            )
        ).first()

        if existing:
            skipped.append(sym_data["symbol"])
            continue

        new_symbol = Symbol(
            exchange="yahoo",
            symbol_type=sym_data["symbol_type"],
            symbol=sym_data["symbol"],
            display_name=sym_data["display_name"],
            is_active=True,
        )
        db.add(new_symbol)
        created.append(sym_data["symbol"])

    db.commit()

    return {
        "message": "Symbol seeding completed",
        "created": created,
        "skipped": skipped,
        "total_created": len(created),
        "total_skipped": len(skipped),
    }
