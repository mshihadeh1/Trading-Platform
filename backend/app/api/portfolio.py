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


@router.get("/performance")
async def get_portfolio_performance(db: Session = Depends(get_db)):
    trades = db.exec(
        select(PaperTrade, Symbol)
        .join(Symbol, Symbol.symbol_id == PaperTrade.symbol_id)
        .order_by(PaperTrade.exit_time.asc(), PaperTrade.entry_time.asc())
    ).all()
    closed = [(trade, symbol) for trade, symbol in trades if trade.status != "open"]
    open_trades = [(trade, symbol) for trade, symbol in trades if trade.status == "open"]

    equity = settings.initial_capital
    peak = equity
    max_drawdown = 0.0
    equity_curve = []
    monthly_pnl: dict[str, float] = {}
    symbol_pnl: dict[str, float] = {}
    wins = 0
    losses = 0
    gross_profit = 0.0
    gross_loss = 0.0

    for trade, symbol in closed:
        pnl = float(trade.pnl or 0.0)
        equity += pnl
        if pnl > 0:
            wins += 1
            gross_profit += pnl
        else:
            losses += 1
            gross_loss += abs(pnl)
        month_key = (trade.exit_time or trade.entry_time).strftime("%Y-%m")
        monthly_pnl[month_key] = round(monthly_pnl.get(month_key, 0.0) + pnl, 2)
        symbol_pnl[symbol.symbol] = round(symbol_pnl.get(symbol.symbol, 0.0) + pnl, 2)
        if equity > peak:
            peak = equity
        drawdown = ((peak - equity) / peak * 100.0) if peak else 0.0
        max_drawdown = max(max_drawdown, drawdown)
        equity_curve.append({
            "timestamp": (trade.exit_time or trade.entry_time).isoformat(),
            "equity": round(equity, 2),
            "pnl": round(pnl, 2),
            "drawdown_pct": round(drawdown, 2),
        })

    for trade, symbol in open_trades:
        _refresh_trade_mark_to_market(db, trade, symbol)
    db.commit()

    unrealized_pnl = sum(float(trade.pnl or 0.0) for trade, _ in open_trades)
    closed_count = len(closed)
    total_return = equity - settings.initial_capital
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else (999 if gross_profit > 0 else 0)
    avg_win = gross_profit / wins if wins else 0.0
    avg_loss = -(gross_loss / losses) if losses else 0.0

    return {
        "initial_capital": settings.initial_capital,
        "current_equity": round(equity + unrealized_pnl, 2),
        "closed_equity": round(equity, 2),
        "total_return": round(total_return, 2),
        "total_return_pct": round((total_return / settings.initial_capital * 100.0) if settings.initial_capital else 0.0, 2),
        "realized_pnl": round(total_return, 2),
        "unrealized_pnl": round(unrealized_pnl, 2),
        "total_trades": closed_count,
        "open_positions": len(open_trades),
        "win_rate": round((wins / closed_count * 100.0) if closed_count else 0.0, 2),
        "profit_factor": round(profit_factor, 2),
        "avg_win": round(avg_win, 2),
        "avg_loss": round(avg_loss, 2),
        "max_drawdown": round(max_drawdown, 2),
        "monthly_pnl": monthly_pnl,
        "symbol_pnl": symbol_pnl,
        "equity_curve": equity_curve,
    }


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
