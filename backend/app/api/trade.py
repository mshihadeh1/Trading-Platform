"""Paper trading API."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from app.database import get_db
from app.models.trade import Trade, TradeCreate, TradeResponse
from app.worker.tasks import check_paper_trades

router = APIRouter(prefix="/api/trades", tags=["trades"])


class TradeExecRequest(BaseModel):
    symbol: str
    exchange: str = "HYPERLIQUID"
    side: str  # "buy" or "sell"
    quantity: float
    price: float
    stop_loss: float = None
    take_profit: float = None


@router.post("/execute")
def execute_trade(req: TradeExecRequest, db: Session = Depends(get_db)):
    """Execute a paper trade."""
    trade = Trade(
        symbol=req.symbol,
        exchange=req.exchange,
        side=req.side.lower(),
        entry_price=req.price,
        quantity=req.quantity,
        stop_loss=req.stop_loss,
        take_profit=req.take_profit,
        status="open",
        trading_mode="paper",
    )
    db.add(trade)
    db.commit()
    db.refresh(trade)
    return {
        "id": trade.id,
        "symbol": trade.symbol,
        "side": trade.side,
        "entry_price": trade.entry_price,
        "quantity": trade.quantity,
        "stop_loss": trade.stop_loss,
        "take_profit": trade.take_profit,
        "status": trade.status,
    }


@router.get("/")
def list_trades(status: str = None, db: Session = Depends(get_db)):
    query = select(Trade)
    if status:
        query = query.where(Trade.status == status)
    query = query.order_by(Trade.created_at.desc()).limit(100)
    trades = db.exec(query).all()
    return [
        {
            "id": t.id,
            "symbol": t.symbol,
            "exchange": t.exchange,
            "side": t.side,
            "entry_price": t.entry_price,
            "quantity": t.quantity,
            "current_price": t.current_price,
            "stop_loss": t.stop_loss,
            "take_profit": t.take_profit,
            "pnl": t.pnl,
            "pnl_percent": t.pnl_percent,
            "status": t.status,
            "trading_mode": t.trading_mode,
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "closed_at": t.closed_at.isoformat() if t.closed_at else None,
        }
        for t in trades
    ]


@router.get("/portfolio")
def portfolio(db: Session = Depends(get_db)):
    """Get portfolio summary."""
    open_trades = db.query(Trade).filter(
        Trade.status == "open",
        Trade.trading_mode == "paper",
    ).all()

    closed_trades = db.query(Trade).filter(
        Trade.status == "closed",
        Trade.trading_mode == "paper",
    ).all()

    total_pnl = sum(t.pnl for t in closed_trades)
    unrealized_pnl = 0  # Would need real-time prices
    win_count = sum(1 for t in closed_trades if t.pnl > 0)
    loss_count = sum(1 for t in closed_trades if t.pnl <= 0)

    return {
        "open_positions": len(open_trades),
        "total_trades": len(closed_trades),
        "total_pnl": round(total_pnl, 2),
        "unrealized_pnl": round(unrealized_pnl, 2),
        "win_rate": round(win_count / (win_count + loss_count) * 100, 2) if (win_count + loss_count) > 0 else 0,
        "open_trade_list": [
            {
                "id": t.id,
                "symbol": t.symbol,
                "side": t.side,
                "entry_price": t.entry_price,
                "quantity": t.quantity,
                "stop_loss": t.stop_loss,
                "take_profit": t.take_profit,
            }
            for t in open_trades
        ],
    }


@router.post("/check")
def check_trades():
    """Manually trigger paper trade checks."""
    result = check_paper_trades.delay()
    return {"task_id": result.id}
