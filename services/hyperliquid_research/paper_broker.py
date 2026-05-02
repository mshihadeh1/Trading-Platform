"""Paper-only execution engine for Hyperliquid research strategies."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass(slots=True)
class RiskConfig:
    initial_cash_usd: float = 10_000.0
    max_risk_per_trade_pct: float = 0.005
    max_daily_loss_pct: float = 0.02
    max_weekly_loss_pct: float = 0.05
    max_open_positions: int = 2
    leverage: float = 1.0
    max_leverage_allowed: float = 2.0
    default_stop_loss_pct: float = 0.01
    take_profit_R: float = 1.8
    max_trades_per_day: int = 2
    fee_bps: float = 4.0
    slippage_bps: float = 5.0


class PaperBroker:
    """Simulates entries/exits. Contains no live trading adapter."""

    def __init__(self, config: RiskConfig | None = None) -> None:
        self.config = config or RiskConfig()
        if self.config.leverage > self.config.max_leverage_allowed:
            raise ValueError("Paper leverage cannot exceed max_leverage_allowed")
        self.cash = self.config.initial_cash_usd
        self.positions: dict[str, dict[str, Any]] = {}
        self.events: list[dict[str, Any]] = []
        self.daily_realized_pnl = 0.0
        self.trades_today = 0

    def process_signal(self, signal: dict[str, Any], mark_price: float) -> dict[str, Any]:
        side = signal.get("side")
        symbol = str(signal.get("symbol"))
        if side not in {"long", "short"}:
            return self._record("skipped", symbol=symbol, reason="signal side is none", signal=signal)
        if symbol in self.positions:
            return self._record("skipped", symbol=symbol, reason="open position already exists; no averaging down", signal=signal)
        if len(self.positions) >= self.config.max_open_positions:
            return self._record("skipped", symbol=symbol, reason="max open positions reached", signal=signal)
        if self.trades_today >= self.config.max_trades_per_day:
            return self._record("skipped", symbol=symbol, reason="max trades per day reached", signal=signal)
        if self.daily_realized_pnl <= -self.config.initial_cash_usd * self.config.max_daily_loss_pct:
            return self._record("skipped", symbol=symbol, reason="max daily loss reached", signal=signal)

        stop = _float(signal.get("suggested_stop"))
        entry = float(mark_price)
        if stop is None or stop <= 0 or entry <= 0:
            stop = entry * (1 - self.config.default_stop_loss_pct) if side == "long" else entry * (1 + self.config.default_stop_loss_pct)
        per_unit_risk = abs(entry - stop)
        if per_unit_risk <= 0:
            return self._record("skipped", symbol=symbol, reason="invalid stop; zero risk distance", signal=signal)
        max_risk = self.cash * self.config.max_risk_per_trade_pct
        quantity = max_risk / per_unit_risk
        notional = quantity * entry
        max_notional = self.cash * self.config.leverage
        if notional > max_notional:
            quantity = max_notional / entry
            notional = max_notional
        take_profit = _float(signal.get("suggested_take_profit"))
        if take_profit is None:
            take_profit = entry + per_unit_risk * self.config.take_profit_R if side == "long" else entry - per_unit_risk * self.config.take_profit_R
        fee_estimate = notional * (self.config.fee_bps + self.config.slippage_bps) / 10_000.0
        position = {
            "symbol": symbol,
            "side": side,
            "entry_time": _now(),
            "entry_price": entry,
            "quantity": quantity,
            "notional": notional,
            "stop_loss": stop,
            "take_profit": take_profit,
            "max_hold_minutes": signal.get("suggested_max_hold_minutes"),
            "source_signal": signal,
            "max_risk_usd": max_risk,
            "entry_fee_slippage_estimate": fee_estimate,
        }
        self.positions[symbol] = position
        self.trades_today += 1
        return self._record("entry", **position)

    def mark_to_market(self, symbol: str, mark_price: float, timestamp: str | None = None) -> dict[str, Any] | None:
        position = self.positions.get(symbol)
        if not position:
            return None
        side = position["side"]
        exit_reason = None
        if side == "long" and mark_price <= position["stop_loss"]:
            exit_reason = "stop_loss"
        elif side == "long" and mark_price >= position["take_profit"]:
            exit_reason = "take_profit"
        elif side == "short" and mark_price >= position["stop_loss"]:
            exit_reason = "stop_loss"
        elif side == "short" and mark_price <= position["take_profit"]:
            exit_reason = "take_profit"
        if not exit_reason:
            return None
        return self.close_position(symbol, mark_price, exit_reason, timestamp=timestamp)

    def close_position(self, symbol: str, exit_price: float, reason: str, timestamp: str | None = None) -> dict[str, Any]:
        position = self.positions.pop(symbol)
        side = position["side"]
        gross = (exit_price - position["entry_price"]) * position["quantity"] if side == "long" else (position["entry_price"] - exit_price) * position["quantity"]
        fees = position["notional"] * (self.config.fee_bps + self.config.slippage_bps) / 10_000.0
        pnl = gross - fees
        self.cash += pnl
        self.daily_realized_pnl += pnl
        return self._record("exit", symbol=symbol, side=side, exit_time=timestamp or _now(), exit_price=exit_price, pnl=pnl, fees_estimate=fees, funding_estimate=0.0, exit_reason=reason, position=position)

    def _record(self, event: str, **fields: Any) -> dict[str, Any]:
        record = {"event": event, "timestamp": _now(), **fields}
        self.events.append(record)
        return record


def _float(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
