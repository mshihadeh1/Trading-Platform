"""Deterministic research strategies for signal generation."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pandas as pd


def trend_flow_signal(symbol: str, features: pd.DataFrame, market_score: dict[str, Any] | None = None, majors_regime: str | None = None) -> dict[str, Any]:
    """BTC/ETH/SOL trend-flow baseline signal with explicit pass/fail logging."""
    ctx = market_score or {}
    if features is None or features.empty:
        return _signal(symbol, "none", 0, [], ["missing features"], None, None, ["No candle feature data available"])
    latest = features.iloc[-1]
    price = _float(latest.get("close"))
    atr_proxy = max(price * 0.0075, price * abs(_float(latest.get("return_1h"), 0.005))) if price else None
    long_checks = {
        "price above VWAP": price is not None and price > _float(latest.get("vwap"), 10**18),
        "EMA 9 above EMA 20/50": _float(latest.get("ema_9")) > _float(latest.get("ema_20")) > _float(latest.get("ema_50")),
        "15m range breakout": bool(latest.get("range_breakout_15m")),
        "volume expansion": bool(latest.get("volume_expansion")),
        "funding not overheated": abs(_float(ctx.get("funding_rate"), 0.0)) < 0.001,
        "majors risk-on or neutral": majors_regime in {None, "risk_on", "neutral"},
    }
    short_checks = {
        "price below VWAP": price is not None and price < _float(latest.get("vwap"), -1),
        "EMA 9 below EMA 20/50": _float(latest.get("ema_9")) < _float(latest.get("ema_20")) < _float(latest.get("ema_50")),
        "15m range breakdown": bool(latest.get("range_breakdown_15m")),
        "volume expansion": bool(latest.get("volume_expansion")),
        "funding not extremely negative": _float(ctx.get("funding_rate"), 0.0) > -0.001,
        "majors risk-off or neutral": majors_regime in {None, "risk_off", "neutral"},
    }
    long_passes = [k for k, v in long_checks.items() if v]
    short_passes = [k for k, v in short_checks.items() if v]
    if len(long_passes) >= 5:
        stop = price - atr_proxy if price and atr_proxy else None
        tp = price + (price - stop) * 1.8 if price and stop else None
        return _signal(symbol, "long", len(long_passes) / len(long_checks), long_passes, [k for k, v in long_checks.items() if not v], stop, tp, [])
    if len(short_passes) >= 5:
        stop = price + atr_proxy if price and atr_proxy else None
        tp = price - (stop - price) * 1.8 if price and stop else None
        return _signal(symbol, "short", len(short_passes) / len(short_checks), short_passes, [k for k, v in short_checks.items() if not v], stop, tp, [])
    checks = long_checks if len(long_passes) >= len(short_passes) else short_checks
    return _signal(symbol, "none", max(len(long_passes), len(short_passes)) / len(checks), long_passes or short_passes, [k for k, v in checks.items() if not v], None, None, ["No trade unless enough deterministic checks pass"])


def stock_index_placeholder_signal(symbol: str, features: pd.DataFrame, market_score: dict[str, Any], underlying_confirmed: bool | None = None) -> dict[str, Any]:
    """AI stock/index-like perp placeholder without black-box AI decision-making."""
    if not market_score.get("tradable_candidate"):
        return _signal(symbol, "none", 0, [], ["market audit did not pass"], None, None, [market_score.get("reject_reason", "Rejected by market audit")])
    if features is None or features.empty:
        return _signal(symbol, "none", 0, [], ["missing features"], None, None, ["No candle feature data available"])
    latest = features.iloc[-1]
    price = _float(latest.get("close"))
    long_checks = {
        "U.S. market hours": bool(latest.get("is_us_market_hours")),
        "perp above VWAP": price is not None and price > _float(latest.get("vwap"), 10**18),
        "breaks opening range high": price is not None and price > _float(latest.get("opening_range_high"), 10**18),
        "liquidity acceptable": market_score.get("tradable_candidate") is True,
        "underlying confirms or unavailable": underlying_confirmed in {True, None},
    }
    short_checks = {
        "U.S. market hours": bool(latest.get("is_us_market_hours")),
        "perp below VWAP": price is not None and price < _float(latest.get("vwap"), -1),
        "breaks opening range low": price is not None and price < _float(latest.get("opening_range_low"), -1),
        "liquidity acceptable": market_score.get("tradable_candidate") is True,
        "underlying confirms or unavailable": underlying_confirmed in {False, None},
    }
    for side, checks in (("long", long_checks), ("short", short_checks)):
        passes = [k for k, v in checks.items() if v]
        if len(passes) == len(checks):
            stop = price * (0.992 if side == "long" else 1.008) if price else None
            tp = price + (price - stop) * 1.8 if side == "long" and price and stop else price - (stop - price) * 1.8 if price and stop else None
            return _signal(symbol, side, 0.75, passes, [], stop, tp, ["Placeholder: catalyst/AI classifier not wired in Phase 1"])
    checks = long_checks
    return _signal(symbol, "none", 0.0, [k for k, v in checks.items() if v], [k for k, v in checks.items() if not v], None, None, ["No stock/index trade unless audit, hours, VWAP, OR break, and underlying checks pass"])


def _signal(symbol: str, side: str, confidence: float, reason: list[str], failed: list[str], stop: float | None, tp: float | None, notes: list[str]) -> dict[str, Any]:
    return {
        "symbol": symbol,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "side": side,
        "confidence_score": round(float(confidence), 4),
        "reason": reason,
        "failed_checks": failed,
        "suggested_stop": round(stop, 8) if stop is not None else None,
        "suggested_take_profit": round(tp, 8) if tp is not None else None,
        "suggested_max_hold_minutes": 240 if side != "none" else 0,
        "risk_notes": notes,
    }


def _float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or pd.isna(value):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default
