"""Risk management API."""

from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.config import settings
from app.services.risk_management import PositionSizeRequestData, calculate_position_size

router = APIRouter()


class PositionSizeRequest(BaseModel):
    symbol: str = ""
    direction: Literal["long", "short"] = "long"
    entry_price: float = Field(gt=0)
    stop_loss: float = Field(gt=0)
    account_equity: float | None = Field(default=None, gt=0)
    method: Literal["fixed_fractional", "volatility_atr", "kelly"] = "fixed_fractional"
    risk_pct: float | None = Field(default=None, ge=0, le=100)
    atr: float | None = Field(default=None, gt=0)
    atr_multiple: float = Field(default=2.0, gt=0)
    win_rate: float | None = Field(default=None, ge=0, le=100)
    reward_risk: float | None = Field(default=None, gt=0)
    max_position_pct: float | None = Field(default=None, gt=0, le=100)
    max_risk_pct: float = Field(default=5.0, gt=0, le=100)


@router.get("/profile")
async def get_risk_profile():
    return {
        "initial_capital": settings.initial_capital,
        "max_position_pct": settings.max_position_pct,
        "max_open_trades": settings.max_open_trades,
        "min_risk_reward_ratio": settings.min_risk_reward_ratio,
        "auto_trade_enabled": settings.auto_trade_enabled,
        "sizing_methods": ["fixed_fractional", "volatility_atr", "kelly"],
        "default_risk_pct": 1.0,
        "max_risk_pct": 5.0,
    }


@router.post("/position-size")
async def position_size(item: PositionSizeRequest):
    try:
        return calculate_position_size(
            PositionSizeRequestData(
                symbol=item.symbol,
                direction=item.direction,
                entry_price=item.entry_price,
                stop_loss=item.stop_loss,
                account_equity=item.account_equity or settings.initial_capital,
                method=item.method,
                risk_pct=item.risk_pct,
                atr=item.atr,
                atr_multiple=item.atr_multiple,
                win_rate=item.win_rate,
                reward_risk=item.reward_risk,
                max_position_pct=item.max_position_pct or settings.max_position_pct,
                max_risk_pct=item.max_risk_pct,
            )
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
