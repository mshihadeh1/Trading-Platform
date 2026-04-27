"""Technical indicator computation using pandas_ta."""

import logging
from typing import List, Optional

import pandas as pd

logger = logging.getLogger(__name__)


def compute(candles: List[dict]) -> dict:
    """
    Compute all technical indicators from a list of candle dicts.
    Returns a dict of indicator values (floats) plus a price_action_summary string.
    """
    if not candles or len(candles) < 50:
        return {"price_action_summary": "Insufficient data for analysis"}

    df = pd.DataFrame(candles)
    df = df.sort_values("timestamp").reset_index(drop=True)

    if len(df) < 50:
        return {"price_action_summary": "Insufficient data for analysis"}

    # --- EMA ---
    df["ema_20"] = df["close"].ewm(span=20, adjust=False).mean()
    df["ema_50"] = df["close"].ewm(span=50, adjust=False).mean()
    df["ema_200"] = df["close"].ewm(span=200, adjust=False).mean() if len(df) >= 200 else None

    # --- RSI ---
    df["rsi"] = _rsi(df["close"], period=14)

    # --- MACD ---
    df["macd"] = df["close"].ewm(span=12, adjust=False).mean() - df["close"].ewm(span=26, adjust=False).mean()
    df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()
    df["macd_hist"] = df["macd"] - df["macd_signal"]

    # --- Bollinger Bands ---
    df["bb_middle"] = df["close"].rolling(window=20).mean()
    df["bb_std"] = df["close"].rolling(window=20).std()
    df["bb_upper"] = df["bb_middle"] + 2 * df["bb_std"]
    df["bb_lower"] = df["bb_middle"] - 2 * df["bb_std"]
    df["bb_position"] = (df["close"] - df["bb_lower"]) / (df["bb_upper"] - df["bb_lower"]) if (df["bb_upper"] - df["bb_lower"]).iloc[-1] > 0 else 0.5

    # --- ATR ---
    df["high_low"] = df["high"] - df["low"]
    df["high_prevclose"] = df["high"] - df["close"].shift(1)
    df["low_prevclose"] = df["close"].shift(1) - df["low"]
    df["tr"] = df[["high_low", "high_prevclose", "low_prevclose"]].max(axis=1)
    df["atr"] = df["tr"].rolling(window=14).mean()

    # --- Volume ---
    df["volume_sma_20"] = df["volume"].rolling(window=20).mean()
    df["volume_ratio"] = df["volume"] / df["volume_sma_20"]

    # Get latest values
    latest = df.iloc[-1]
    prev = df.iloc[-2]

    result = {
        "rsi": float(latest["rsi"]) if not pd.isna(latest.get("rsi")) else None,
        "macd": float(latest["macd"]) if not pd.isna(latest.get("macd")) else None,
        "macd_signal": float(latest["macd_signal"]) if not pd.isna(latest.get("macd_signal")) else None,
        "macd_hist": float(latest["macd_hist"]) if not pd.isna(latest.get("macd_hist")) else None,
        "bb_upper": float(latest["bb_upper"]) if not pd.isna(latest.get("bb_upper")) else None,
        "bb_middle": float(latest["bb_middle"]) if not pd.isna(latest.get("bb_middle")) else None,
        "bb_lower": float(latest["bb_lower"]) if not pd.isna(latest.get("bb_lower")) else None,
        "bb_position": float(latest["bb_position"]) if not pd.isna(latest.get("bb_position")) else None,
        "ema_20": float(latest["ema_20"]) if not pd.isna(latest.get("ema_20")) else None,
        "ema_50": float(latest["ema_50"]) if not pd.isna(latest.get("ema_50")) else None,
        "ema_200": float(latest["ema_200"]) if not pd.isna(latest.get("ema_200")) else None,
        "atr": float(latest["atr"]) if not pd.isna(latest.get("atr")) else None,
        "volume_ratio": float(latest["volume_ratio"]) if not pd.isna(latest.get("volume_ratio")) else None,
    }

    # Price action summary
    close = float(latest["close"])
    sma_20 = float(latest["bb_middle"]) if not pd.isna(latest["bb_middle"]) else close
    ema_20 = float(latest["ema_20"]) if not pd.isna(latest["ema_20"]) else close
    ema_50 = float(latest["ema_50"]) if not pd.isna(latest["ema_50"]) else close
    rsi_val = float(latest["rsi"]) if not pd.isna(latest["rsi"]) else 50
    vol_ratio = float(latest["volume_ratio"]) if not pd.isna(latest["volume_ratio"]) else 1.0

    trend = "bullish" if close > ema_20 > ema_50 else ("bearish" if close < ema_20 < ema_50 else "neutral")
    rsi_zone = "oversold" if rsi_val < 30 else ("overbought" if rsi_val > 70 else "neutral")
    vol_label = "above average" if vol_ratio > 1.2 else ("below average" if vol_ratio < 0.8 else "normal")

    result["price_action_summary"] = (
        f"Price: ${close:.2f} | Trend: {trend} | RSI: {rsi_val:.1f} ({rsi_zone}) | "
        f"Volume: {vol_label} ({vol_ratio:.1f}x)"
    )

    return result


def _rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """Compute RSI."""
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = (-delta.clip(upper=0)).clip(lower=0)
    avg_gain = gain.ewm(alpha=1/period, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1/period, min_periods=period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))
