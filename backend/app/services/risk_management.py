"""Risk management and position sizing helpers."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PositionSizeRequestData:
    symbol: str
    direction: str
    entry_price: float
    stop_loss: float
    account_equity: float
    method: str = "fixed_fractional"
    risk_pct: float | None = None
    atr: float | None = None
    atr_multiple: float = 2.0
    win_rate: float | None = None
    reward_risk: float | None = None
    max_position_pct: float = 25.0
    max_risk_pct: float = 5.0


def calculate_position_size(item: PositionSizeRequestData) -> dict:
    """Calculate a recommended position size from entry/stop and sizing method."""
    _validate_positive("entry_price", item.entry_price)
    _validate_positive("stop_loss", item.stop_loss)
    _validate_positive("account_equity", item.account_equity)

    risk_per_unit = abs(item.entry_price - item.stop_loss)
    if risk_per_unit <= 0:
        raise ValueError("Entry price and stop loss must be different")

    warnings: list[str] = []
    recommended_risk_pct = _recommended_risk_pct(item)
    recommended_risk_pct = max(0.0, min(recommended_risk_pct, item.max_risk_pct))

    risk_amount = item.account_equity * recommended_risk_pct / 100.0
    quantity = risk_amount / risk_per_unit
    notional = quantity * item.entry_price
    max_notional = item.account_equity * item.max_position_pct / 100.0

    if notional > max_notional:
        quantity = max_notional / item.entry_price
        notional = max_notional
        risk_amount = quantity * risk_per_unit
        warnings.append(f"Position capped at {item.max_position_pct:.1f}% max notional exposure")

    position_pct = (notional / item.account_equity * 100.0) if item.account_equity else 0.0
    actual_risk_pct = (risk_amount / item.account_equity * 100.0) if item.account_equity else 0.0

    return {
        "symbol": item.symbol,
        "direction": item.direction,
        "method": item.method,
        "entry_price": round(item.entry_price, 8),
        "stop_loss": round(item.stop_loss, 8),
        "risk_per_unit": round(risk_per_unit, 8),
        "recommended_risk_pct": round(recommended_risk_pct, 4),
        "actual_risk_pct": round(actual_risk_pct, 4),
        "risk_amount": round(risk_amount, 2),
        "quantity": round(quantity, 8),
        "notional": round(notional, 2),
        "position_pct": round(position_pct, 4),
        "max_position_pct": item.max_position_pct,
        "warnings": warnings,
    }


def _recommended_risk_pct(item: PositionSizeRequestData) -> float:
    method = item.method.lower()
    if method == "fixed_fractional":
        return item.risk_pct if item.risk_pct is not None else 1.0
    if method == "volatility_atr":
        if not item.atr or item.atr <= 0:
            raise ValueError("ATR must be positive for volatility_atr sizing")
        # Wider ATR stops reduce the risk percentage; tighter quiet markets can use a little more.
        atr_stop_distance = item.atr * max(item.atr_multiple, 0.1)
        price_risk_pct = atr_stop_distance / item.entry_price * 100.0
        return max(0.25, min(2.0, 2.0 / max(price_risk_pct, 0.1)))
    if method == "kelly":
        win_rate = item.win_rate if item.win_rate is not None else 0.5
        reward_risk = item.reward_risk if item.reward_risk is not None else 1.5
        if win_rate > 1:
            win_rate = win_rate / 100.0
        win_rate = max(0.0, min(win_rate, 1.0))
        reward_risk = max(reward_risk, 0.01)
        # Kelly fraction: W - (1-W)/R. Use quarter Kelly for safer trading helper behavior.
        full_kelly = win_rate - ((1 - win_rate) / reward_risk)
        return max(0.0, full_kelly * 100.0 * 0.25)
    raise ValueError(f"Unsupported sizing method: {item.method}")


def _validate_positive(name: str, value: float) -> None:
    if value <= 0:
        raise ValueError(f"{name} must be positive")
