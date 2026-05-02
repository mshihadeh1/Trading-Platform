"""Isolated external equity/ETF data interface for stock/index-like perp confirmation."""

from __future__ import annotations

from typing import Any

import pandas as pd

SYMBOL_MAP = {
    "SPX": "^GSPC",
    "SPY": "SPY",
    "QQQ": "QQQ",
    "NDX": "^NDX",
    "AAPL": "AAPL",
    "MSFT": "MSFT",
    "NVDA": "NVDA",
    "TSLA": "TSLA",
    "META": "META",
    "AMZN": "AMZN",
    "GOOGL": "GOOGL",
    "COIN": "COIN",
    "MSTR": "MSTR",
}


def map_hyperliquid_symbol_to_underlying(symbol: str) -> str | None:
    normalized = symbol.upper().replace("-PERP", "")
    if normalized.startswith("U") and normalized[1:] in SYMBOL_MAP:
        normalized = normalized[1:]
    return SYMBOL_MAP.get(normalized)


def get_underlying_quote(symbol: str) -> dict[str, Any]:
    underlying = map_hyperliquid_symbol_to_underlying(symbol)
    if not underlying:
        return {"symbol": symbol, "underlying": None, "available": False, "reason": "no mapping"}
    try:
        import yfinance as yf

        ticker = yf.Ticker(underlying)
        hist = ticker.history(period="1d", interval="1m")
        if hist.empty:
            return {"symbol": symbol, "underlying": underlying, "available": False, "reason": "empty yfinance response"}
        last = hist.iloc[-1]
        return {"symbol": symbol, "underlying": underlying, "available": True, "price": float(last["Close"]), "timestamp": str(hist.index[-1])}
    except Exception as exc:  # pragma: no cover - network/library behavior varies
        return {"symbol": symbol, "underlying": underlying, "available": False, "reason": str(exc)}


def get_underlying_candles(symbol: str, interval: str = "15m", period: str = "5d") -> pd.DataFrame:
    underlying = map_hyperliquid_symbol_to_underlying(symbol)
    if not underlying:
        return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])
    try:
        import yfinance as yf

        hist = yf.download(underlying, period=period, interval=interval, progress=False, auto_adjust=False)
        if hist.empty:
            return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])
        hist = hist.reset_index()
        return pd.DataFrame(
            {
                "timestamp": pd.to_datetime(hist.iloc[:, 0], utc=True),
                "open": hist["Open"].astype(float),
                "high": hist["High"].astype(float),
                "low": hist["Low"].astype(float),
                "close": hist["Close"].astype(float),
                "volume": hist["Volume"].astype(float),
            }
        )
    except Exception:  # pragma: no cover
        return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])
