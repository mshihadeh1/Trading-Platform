"""Reusable strategy templates for common technical setups."""

from __future__ import annotations

STRATEGY_TEMPLATES: list[dict] = [
    {
        "id": "rsi_reversal",
        "name": "RSI Reversal",
        "description": "Mean-reversion setup looking for oversold RSI with improving momentum.",
        "timeframe": "1h",
        "exchange": "hyperliquid",
        "category": "mean_reversion",
        "conditions": [
            {"indicator": "rsi", "operator": "lt", "value": 32},
            {"indicator": "bb_position", "operator": "lt", "value": 0.25},
            {"indicator": "volume_ratio", "operator": "gt", "value": 0.8},
        ],
        "risk_profile": {"default_risk_pct": 0.75, "stop_atr_multiple": 1.5, "target_reward_risk": 2.0},
    },
    {
        "id": "macd_trend",
        "name": "MACD Trend Continuation",
        "description": "Trend-following setup using MACD histogram strength and EMA alignment.",
        "timeframe": "1h",
        "exchange": "hyperliquid",
        "category": "trend_following",
        "conditions": [
            {"indicator": "macd_hist", "operator": "gt", "value": 0},
            {"indicator": "ema_20_above_ema_50", "operator": "eq", "value": 1},
            {"indicator": "volume_ratio", "operator": "gt", "value": 1.0},
        ],
        "risk_profile": {"default_risk_pct": 1.0, "stop_atr_multiple": 2.0, "target_reward_risk": 2.5},
    },
    {
        "id": "bollinger_squeeze",
        "name": "Bollinger Squeeze Breakout",
        "description": "Breakout template for volatility compression followed by volume expansion.",
        "timeframe": "1h",
        "exchange": "hyperliquid",
        "category": "breakout",
        "conditions": [
            {"indicator": "bb_width_pct", "operator": "lt", "value": 4.0},
            {"indicator": "volume_ratio", "operator": "gt", "value": 1.2},
            {"indicator": "close_above_ema_20", "operator": "eq", "value": 1},
        ],
        "risk_profile": {"default_risk_pct": 0.8, "stop_atr_multiple": 2.0, "target_reward_risk": 3.0},
    },
    {
        "id": "ema_pullback",
        "name": "EMA Trend Pullback",
        "description": "Buy shallow pullbacks in an established EMA uptrend.",
        "timeframe": "4h",
        "exchange": "hyperliquid",
        "category": "pullback",
        "conditions": [
            {"indicator": "ema_20_above_ema_50", "operator": "eq", "value": 1},
            {"indicator": "close_above_ema_20", "operator": "eq", "value": 1},
            {"indicator": "rsi", "operator": "gt", "value": 45},
        ],
        "risk_profile": {"default_risk_pct": 1.0, "stop_atr_multiple": 1.8, "target_reward_risk": 2.0},
    },
    {
        "id": "volume_breakout",
        "name": "Volume Breakout",
        "description": "Momentum breakout setup requiring strong relative volume and bullish structure.",
        "timeframe": "1h",
        "exchange": "hyperliquid",
        "category": "momentum",
        "conditions": [
            {"indicator": "volume_ratio", "operator": "gt", "value": 1.8},
            {"indicator": "close_above_ema_20", "operator": "eq", "value": 1},
            {"indicator": "rsi", "operator": "gt", "value": 55},
        ],
        "risk_profile": {"default_risk_pct": 0.75, "stop_atr_multiple": 2.5, "target_reward_risk": 3.0},
    },
]


def list_templates() -> list[dict]:
    return STRATEGY_TEMPLATES


def get_template(template_id: str) -> dict | None:
    return next((item for item in STRATEGY_TEMPLATES if item["id"] == template_id), None)
