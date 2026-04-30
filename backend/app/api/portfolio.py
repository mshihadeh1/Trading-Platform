from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.config import settings
from app.database import get_db
from app.models.candle import Candle
from app.models.paper_trade import PaperTrade
from app.models.symbol import Symbol
from app.schemas.paper_trade import PaperTradeCreate, PortfolioSummary
from app.services.yahoo_finance import get_current_price

router = APIRouter()


@router.get("/summary", response_model=PortfolioSummary)
async def get_portfolio_summary(db: Session = Depends(get_db)):
    trades = db.exec(select(PaperTrade, Symbol).join(Symbol, Symbol.symbol_id == PaperTrade.symbol_id)).all()

    open_trades: list[tuple[PaperTrade, Symbol]] = []
    closed_trades: list[tuple[PaperTrade, Symbol]] = []
    for trade, symbol in trades:
        if trade.status == "open":
            _refresh_trade_mark_to_market(db, trade, symbol)
            open_trades.append((trade, symbol))
        else:
            closed_trades.append((trade, symbol))

    realized_pnl = sum(trade.pnl for trade, _ in closed_trades)
    unrealized_pnl = sum(trade.pnl for trade, _ in open_trades)
    total_pnl = realized_pnl + unrealized_pnl
    wins = len([trade for trade, _ in closed_trades if trade.pnl > 0])
    win_rate = (wins / len(closed_trades) * 100) if closed_trades else 0.0
    db.commit()

    return PortfolioSummary(
        total_pnl=round(total_pnl, 2),
        total_pnl_pct=round((total_pnl / settings.initial_capital) * 100, 2) if settings.initial_capital else 0.0,
        realized_pnl=round(realized_pnl, 2),
        unrealized_pnl=round(unrealized_pnl, 2),
        open_positions=len(open_trades),
        total_trades=len(closed_trades),
        win_rate=round(win_rate, 2),
        current_equity=round(settings.initial_capital + total_pnl, 2),
    )


@router.get("")
async def get_trades(db: Session = Depends(get_db)):
    trades = db.exec(
        select(PaperTrade, Symbol)
        .join(Symbol, Symbol.symbol_id == PaperTrade.symbol_id)
        .order_by(PaperTrade.entry_time.desc())
    ).all()
    payload = []
    for trade, symbol in trades:
        if trade.status == "open":
            _refresh_trade_mark_to_market(db, trade, symbol)
        payload.append(_serialize_trade(trade, symbol))
    db.commit()
    return payload


@router.post("", status_code=201)
async def create_trade(item: PaperTradeCreate, db: Session = Depends(get_db)):
    symbol = db.get(Symbol, item.symbol_id)
    if not symbol:
        raise HTTPException(status_code=404, detail="Symbol not found")

    if item.entry_price <= 0 or item.quantity <= 0:
        raise HTTPException(status_code=400, detail="Entry price and quantity must be positive")

    trade = PaperTrade(
        **item.model_dump(),
        current_price=item.entry_price,
    )
    db.add(trade)
    db.commit()
    db.refresh(trade)
    return _serialize_trade(trade, symbol)


def _refresh_trade_mark_to_market(db: Session, trade: PaperTrade, symbol: Symbol) -> None:
    price = _current_price(db, symbol)
    if price is None:
        return
    trade.current_price = round(price, 8)
    if trade.direction == "long":
        pnl = (price - trade.entry_price) * trade.quantity
    else:
        pnl = (trade.entry_price - price) * trade.quantity
    trade.pnl = round(pnl, 2)
    trade.pnl_pct = round((pnl / (trade.entry_price * trade.quantity)) * 100, 2) if trade.entry_price else 0.0


def _current_price(db: Session, symbol: Symbol) -> float | None:
    if symbol.exchange == "yahoo":
        live = get_current_price(symbol.symbol)
        if live is not None:
            return live

    latest_candle = db.exec(
        select(Candle)
        .where(Candle.symbol_id == symbol.symbol_id)
        .order_by(Candle.timestamp.desc())
        .limit(1)
    ).first()
    return float(latest_candle.close) if latest_candle else None


def _serialize_trade(trade: PaperTrade, symbol: Symbol) -> dict:
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
