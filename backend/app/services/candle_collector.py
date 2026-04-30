"""Candle collector service for fetching and storing OHLCV data."""

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any

import httpx
import yfinance as yf

from sqlmodel import Session, select
from app.database import get_db
from app.models.symbol import Symbol
from app.models.candle import Candle

logger = logging.getLogger(__name__)


class CandleCollector:
    """Service for collecting and storing candle data from multiple exchanges."""

    def __init__(self, db: Optional[Session] = None):
        self.db = db
        self.hyperliquid_perps = [
            {"symbol": "BTC", "coin": "BTC"},
            {"symbol": "ETH", "coin": "ETH"},
            {"symbol": "SOL", "coin": "SOL"},
            {"symbol": "BNB", "coin": "BNB"},
            {"symbol": "XRP", "coin": "XRP"},
            {"symbol": "DOGE", "coin": "DOGE"},
            {"symbol": "AVAX", "coin": "AVAX"},
            {"symbol": "ARB", "coin": "ARB"},
            {"symbol": "OP", "coin": "OP"},
            {"symbol": "WIF", "coin": "WIF"},
            {"symbol": "PEPE", "coin": "kPEPE"},
            {"symbol": "SUI", "coin": "SUI"},
            {"symbol": "LINK", "coin": "LINK"},
            {"symbol": "AAVE", "coin": "AAVE"},
            {"symbol": "FET", "coin": "FET"},
        ]
        self.yahoo_symbols = [
            {"symbol": "SPY", "display_name": "S&P 500 ETF", "symbol_type": "etf"},
            {"symbol": "QQQ", "display_name": "Nasdaq 100 ETF", "symbol_type": "etf"},
            {"symbol": "AAPL", "display_name": "Apple Inc.", "symbol_type": "stock"},
            {"symbol": "TSLA", "display_name": "Tesla Inc.", "symbol_type": "stock"},
            {"symbol": "NVDA", "display_name": "NVIDIA Corp.", "symbol_type": "stock"},
            {"symbol": "MSFT", "display_name": "Microsoft Corp.", "symbol_type": "stock"},
            {"symbol": "AMZN", "display_name": "Amazon.com Inc.", "symbol_type": "stock"},
            {"symbol": "META", "display_name": "Meta Platforms", "symbol_type": "stock"},
            {"symbol": "GOOGL", "display_name": "Alphabet Inc.", "symbol_type": "stock"},
            {"symbol": "BTC-USD", "display_name": "Bitcoin USD", "symbol_type": "crypto"},
            {"symbol": "ETH-USD", "display_name": "Ethereum USD", "symbol_type": "crypto"},
        ]

    def _get_db(self) -> Session:
        """Get database session."""
        if self.db:
            return self.db
        return next(get_db())

    async def fetch_hyperliquid_candles(
        self,
        symbol: str,
        interval: str = "1h",
        limit: int = 200
    ) -> List[Dict[str, Any]]:
        """
        Fetch historical candles from Hyperliquid.

        Args:
            symbol: Symbol ticker (e.g., "BTC", "ETH")
            interval: Time interval (5m, 15m, 1h, 4h, 1d)
            limit: Number of candles to fetch

        Returns:
            List of candle dictionaries with OHLCV data
        """
        logger.info(f"Fetching Hyperliquid candles for {symbol} ({interval}, limit={limit})")

        timeframe_map = {
            "5m": 300000,
            "15m": 900000,
            "1h": 3600000,
            "4h": 14400000,
            "1d": 86400000,
        }
        ms = timeframe_map.get(interval, 3600000)

        # Find the coin name for this symbol
        coin = symbol
        for perp in self.hyperliquid_perps:
            if perp["symbol"] == symbol:
                coin = perp["coin"]
                break

        end_time = int(datetime.now(timezone.utc).timestamp() * 1000)
        start_time = end_time - (limit * ms)

        async with httpx.AsyncClient(timeout=30.0) as client:
            payload = {
                "type": "candleSnapshot",
                "req": {
                    "coin": coin,
                    "interval": interval,
                    "startTime": start_time,
                    "endTime": end_time,
                },
            }
            try:
                resp = await client.post(
                    "https://api.hyperliquid.xyz/info",
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
                resp.raise_for_status()
                raw = resp.json()

                candles = []
                for c in raw:
                    if isinstance(c, dict):
                        candles.append({
                            "timestamp": datetime.fromtimestamp(c["t"] / 1000, tz=timezone.utc),
                            "open": float(c["o"]),
                            "high": float(c["h"]),
                            "low": float(c["l"]),
                            "close": float(c["c"]),
                            "volume": float(c["v"]),
                        })
                    else:
                        candles.append({
                            "timestamp": datetime.fromtimestamp(c[0] / 1000, tz=timezone.utc),
                            "open": float(c[1]),
                            "high": float(c[2]),
                            "low": float(c[3]),
                            "close": float(c[4]),
                            "volume": float(c[5]),
                        })

                logger.info(f"Fetched {len(candles)} candles for {symbol}")
                return candles

            except httpx.HTTPError as e:
                logger.error(f"HTTP error fetching Hyperliquid candles for {symbol}: {e}")
                return []
            except Exception as e:
                logger.error(f"Error fetching Hyperliquid candles for {symbol}: {e}")
                return []

    def fetch_yahoo_candles(
        self,
        symbol: str,
        period: str = "2y",
        interval: str = "1h"
    ) -> List[Dict[str, Any]]:
        """
        Fetch historical candles from Yahoo Finance.

        Args:
            symbol: Yahoo Finance symbol (e.g., "AAPL", "BTC-USD")
            period: Time period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, max)
            interval: Time interval (1m, 2m, 5m, 15m, 30m, 1h, 1d, 5d, 1wk, 1mo, 3mo)

        Returns:
            List of candle dictionaries with OHLCV data
        """
        logger.info(f"Fetching Yahoo Finance candles for {symbol} ({interval}, period={period})")

        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(period=period, interval=interval)

            if df.empty:
                logger.warning(f"No data returned for {symbol}")
                return []

            candles = []
            for idx, row in df.iterrows():
                ts = idx.tzinfo if idx.tzinfo else timezone.utc
                candles.append({
                    "timestamp": idx.replace(tzinfo=timezone.utc) if idx.tzinfo else idx.replace(tzinfo=timezone.utc),
                    "open": float(row["Open"]),
                    "high": float(row["High"]),
                    "low": float(row["Low"]),
                    "close": float(row["Close"]),
                    "volume": float(row["Volume"]),
                })

            logger.info(f"Fetched {len(candles)} candles for {symbol}")
            return candles

        except Exception as e:
            logger.error(f"Error fetching Yahoo Finance candles for {symbol}: {e}")
            return []

    def store_candles(
        self,
        symbol_id: int,
        candles: List[Dict[str, Any]],
        db: Optional[Session] = None
    ) -> int:
        """
        Store candles in the database.

        Args:
            symbol_id: The symbol ID to associate candles with
            candles: List of candle dictionaries with OHLCV data
            db: Optional database session

        Returns:
            Number of candles stored
        """
        db_session = db or self._get_db()
        stored_count = 0

        try:
            for candle_data in candles:
                # Check if candle already exists
                existing = db_session.exec(
                    select(Candle)
                    .where(
                        Candle.symbol_id == symbol_id,
                        Candle.timestamp == candle_data["timestamp"]
                    )
                ).first()

                if existing:
                    # Update existing candle
                    existing.open = candle_data["open"]
                    existing.high = candle_data["high"]
                    existing.low = candle_data["low"]
                    existing.close = candle_data["close"]
                    existing.volume = candle_data["volume"]
                else:
                    # Insert new candle
                    candle = Candle(
                        symbol_id=symbol_id,
                        timestamp=candle_data["timestamp"],
                        open=candle_data["open"],
                        high=candle_data["high"],
                        low=candle_data["low"],
                        close=candle_data["close"],
                        volume=candle_data["volume"],
                    )
                    db_session.add(candle)
                    stored_count += 1

            db_session.commit()
            logger.info(f"Stored {stored_count} new candles for symbol_id={symbol_id}")
            return stored_count

        except Exception as e:
            db_session.rollback()
            logger.error(f"Error storing candles for symbol_id={symbol_id}: {e}")
            return 0

    async def collect_all_hyperliquid(self, db: Optional[Session] = None) -> Dict[str, int]:
        """
        Collect candles for all Hyperliquid perpetual pairs.

        Args:
            db: Optional database session

        Returns:
            Dictionary mapping symbol to number of candles stored
        """
        db_session = db or self._get_db()
        results = {}

        for perp in self.hyperliquid_perps:
            symbol = perp["symbol"]

            # Find or get symbol_id
            sym = db_session.exec(
                select(Symbol)
                .where(Symbol.symbol == symbol, Symbol.exchange == "hyperliquid")
            ).first()

            if not sym:
                logger.warning(f"Symbol {symbol} not found in database, skipping")
                continue

            candles = await self.fetch_hyperliquid_candles(symbol)
            if candles:
                count = self.store_candles(sym.symbol_id, candles, db_session)
                results[symbol] = count

        return results

    def collect_all_yahoo(self, db: Optional[Session] = None) -> Dict[str, int]:
        """
        Collect candles for all Yahoo Finance symbols.

        Args:
            db: Optional database session

        Returns:
            Dictionary mapping symbol to number of candles stored
        """
        db_session = db or self._get_db()
        results = {}

        for yf_symbol in self.yahoo_symbols:
            symbol = yf_symbol["symbol"]

            # Find or get symbol_id
            sym = db_session.exec(
                select(Symbol)
                .where(Symbol.symbol == symbol, Symbol.exchange == "yahoo")
            ).first()

            if not sym:
                logger.warning(f"Symbol {symbol} not found in database, skipping")
                continue

            candles = self.fetch_yahoo_candles(symbol)
            if candles:
                count = self.store_candles(sym.symbol_id, candles, db_session)
                results[symbol] = count

        return results

    async def collect_symbol(
        self,
        symbol: str,
        exchange: str,
        interval: str = "1h",
        db: Optional[Session] = None
    ) -> int:
        """
        Collect candles for a specific symbol.

        Args:
            symbol: Symbol ticker
            exchange: Exchange name ("hyperliquid" or "yahoo")
            interval: Time interval
            db: Optional database session

        Returns:
            Number of candles stored
        """
        db_session = db or self._get_db()

        # Find symbol_id
        sym = db_session.exec(
            select(Symbol)
            .where(Symbol.symbol == symbol, Symbol.exchange == exchange)
        ).first()

        if not sym:
            logger.error(f"Symbol {symbol} not found on {exchange}")
            return 0

        if exchange == "hyperliquid":
            candles = await self.fetch_hyperliquid_candles(symbol, interval)
        elif exchange == "yahoo":
            candles = self.fetch_yahoo_candles(symbol, interval=interval)
        else:
            logger.error(f"Unsupported exchange: {exchange}")
            return 0

        if candles:
            return self.store_candles(sym.symbol_id, candles, db_session)
        return 0
