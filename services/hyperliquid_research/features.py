"""Feature engineering for Hyperliquid research strategies."""

from __future__ import annotations

from datetime import time as dt_time
from typing import Any

import pandas as pd


def compute_crypto_features(candles: pd.DataFrame, trades: pd.DataFrame | None = None, market_context: dict[str, Any] | None = None) -> pd.DataFrame:
    """Compute deterministic trend/flow features for 24/7 crypto perps."""
    df = _prepare_candles(candles)
    if df.empty:
        return df
    df["vwap"] = _vwap(df)
    df["ema_9"] = df["close"].ewm(span=9, adjust=False).mean()
    df["ema_20"] = df["close"].ewm(span=20, adjust=False).mean()
    df["ema_50"] = df["close"].ewm(span=50, adjust=False).mean()
    df["return_5m"] = df["close"].pct_change(1)
    df["return_15m"] = df["close"].pct_change(1)
    df["return_1h"] = df["close"].pct_change(4)
    df["volume_sma_20"] = df["volume"].rolling(20, min_periods=1).mean()
    df["volume_expansion"] = df["volume"] > (df["volume_sma_20"] * 1.25)
    df["range_high_15m"] = df["high"].shift(1).rolling(4, min_periods=2).max()
    df["range_low_15m"] = df["low"].shift(1).rolling(4, min_periods=2).min()
    df["range_breakout_15m"] = df["close"] > df["range_high_15m"]
    df["range_breakdown_15m"] = df["close"] < df["range_low_15m"]
    df["funding_rate"] = (market_context or {}).get("funding_rate")
    df["open_interest"] = (market_context or {}).get("open_interest")
    df["cvd"] = None
    df["cvd_available"] = False
    if trades is not None and not trades.empty and {"side", "size"}.issubset(trades.columns):
        signed = trades.copy()
        signed["signed_size"] = signed.apply(lambda r: _signed_size(r.get("side"), r.get("size")), axis=1)
        df.loc[df.index[-1], "cvd"] = float(signed["signed_size"].sum())
        df.loc[df.index[-1], "cvd_available"] = True
    return df


def compute_stock_like_features(candles: pd.DataFrame, market_context: dict[str, Any] | None = None, underlying: pd.DataFrame | None = None) -> pd.DataFrame:
    """Compute U.S.-market-hours-aware placeholder features for stock/index-like perps."""
    df = _prepare_candles(candles)
    if df.empty:
        return df
    df["vwap"] = _vwap(df)
    df["is_us_market_hours"] = df["timestamp"].apply(_is_us_market_hours_utc)
    session = df[df["is_us_market_hours"]].copy()
    df["opening_range_high"] = None
    df["opening_range_low"] = None
    if not session.empty:
        first_hour = session.head(4)
        df.loc[df.index, "opening_range_high"] = float(first_hour["high"].max())
        df.loc[df.index, "opening_range_low"] = float(first_hour["low"].min())
    df["relative_volume_proxy"] = df["volume"] / df["volume"].rolling(20, min_periods=1).mean()
    ctx = market_context or {}
    df["mark_oracle_spread_bps"] = _mark_oracle_bps(ctx.get("mark_price"), ctx.get("oracle_price"))
    df["funding_rate"] = ctx.get("funding_rate")
    df["liquidity_quality"] = ctx.get("overall_score")
    df["underlying_confirmed"] = None
    if underlying is not None and not underlying.empty and "close" in underlying.columns:
        df.loc[df.index[-1], "underlying_confirmed"] = float(underlying.iloc[-1]["close"]) > float(underlying.iloc[0]["close"])
    return df


def _prepare_candles(candles: pd.DataFrame) -> pd.DataFrame:
    if candles is None or candles.empty:
        return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])
    df = candles.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df.dropna(subset=["timestamp", "open", "high", "low", "close"]).sort_values("timestamp").reset_index(drop=True)


def _vwap(df: pd.DataFrame) -> pd.Series:
    typical = (df["high"] + df["low"] + df["close"]) / 3.0
    volume = df["volume"].fillna(0).clip(lower=0)
    cumulative_volume = volume.cumsum().replace(0, pd.NA)
    return (typical * volume).cumsum() / cumulative_volume


def _signed_size(side: Any, size: Any) -> float:
    try:
        qty = float(size or 0)
    except (TypeError, ValueError):
        qty = 0.0
    side_text = str(side or "").lower()
    if side_text in {"buy", "b", "long"}:
        return qty
    if side_text in {"sell", "s", "short"}:
        return -qty
    return 0.0


def _is_us_market_hours_utc(ts: pd.Timestamp) -> bool:
    # Phase 1 uses fixed UTC approximation: 14:30-21:00 UTC (ignores DST edge cases).
    t = ts.time()
    return ts.weekday() < 5 and dt_time(14, 30) <= t <= dt_time(21, 0)


def _mark_oracle_bps(mark: Any, oracle: Any) -> float | None:
    try:
        mark_f = float(mark)
        oracle_f = float(oracle)
        return abs((mark_f - oracle_f) / oracle_f * 10_000) if oracle_f else None
    except (TypeError, ValueError):
        return None
