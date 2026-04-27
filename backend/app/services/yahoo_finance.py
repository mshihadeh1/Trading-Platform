"""Yahoo Finance data service."""

import logging
from typing import Optional
from datetime import datetime, timezone

import yfinance as yf

logger = logging.getLogger(__name__)

# Popular Yahoo Finance symbols
YAHOO_POPULAR = [
    {"symbol": "SPY", "display_name": "S&P 500 ETF", "type": "etf"},
    {"symbol": "QQQ", "display_name": "Nasdaq 100 ETF", "type": "etf"},
    {"symbol": "AAPL", "display_name": "Apple Inc.", "type": "stock"},
    {"symbol": "TSLA", "display_name": "Tesla Inc.", "type": "stock"},
    {"symbol": "NVDA", "display_name": "NVIDIA Corp.", "type": "stock"},
    {"symbol": "MSFT", "display_name": "Microsoft Corp.", "type": "stock"},
    {"symbol": "AMZN", "display_name": "Amazon.com Inc.", "type": "stock"},
    {"symbol": "META", "display_name": "Meta Platforms", "type": "stock"},
    {"symbol": "GOOGL", "display_name": "Alphabet Inc.", "type": "stock"},
    {"symbol": "BTC-USD", "display_name": "Bitcoin USD", "type": "crypto"},
    {"symbol": "ETH-USD", "display_name": "Ethereum USD", "type": "crypto"},
]


def search_symbols(query: str) -> list:
    """Search Yahoo Finance for matching symbols."""
    query = query.strip()
    results = []
    for s in YAHOO_POPULAR:
        if query.lower() in s["symbol"].lower() or query.lower() in s["display_name"].lower():
            results.append(s)
    return results


def get_candles(symbol: str, period: str = "2y", interval: str = "1h") -> list:
    """Fetch historical OHLCV candles using yfinance."""
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period, interval=interval)

        if df.empty:
            return []

        candles = []
        for idx, row in df.iterrows():
            # Handle pandas DatetimeIndex — idx is a Timestamp
            ts = idx.tzinfo if idx.tzinfo else timezone.utc
            candles.append({
                "timestamp": ts,
                "open": float(row["Open"]),
                "high": float(row["High"]),
                "low": float(row["Low"]),
                "close": float(row["Close"]),
                "volume": float(row["Volume"]),
            })
        return candles
    except Exception as e:
        logger.error(f"Failed to fetch candles for {symbol}: {e}")
        return []


def get_current_price(symbol: str) -> Optional[float]:
    """Get current price for a symbol."""
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.fast_info
        if hasattr(info, "last_price") and info.last_price:
            return float(info.last_price)
        history = ticker.history(period="1d")
        if not history.empty:
            return float(history["Close"].iloc[-1])
    except Exception as e:
        logger.error(f"Failed to get price for {symbol}: {e}")
    return None
