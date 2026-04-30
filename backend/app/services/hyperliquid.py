"""Hyperliquid market data service."""

import json
import logging
import time
import asyncio
from typing import Optional
from datetime import datetime, timezone

import httpx
import websockets

logger = logging.getLogger(__name__)

# Curated list of Hyperliquid perpetual pairs
HYPERLIQUID_PERPS = [
    {"symbol": "BTC", "display_name": "BTC-PERP", "coin": "BTC"},
    {"symbol": "ETH", "display_name": "ETH-PERP", "coin": "ETH"},
    {"symbol": "SOL", "display_name": "SOL-PERP", "coin": "SOL"},
    {"symbol": "BNB", "display_name": "BNB-PERP", "coin": "BNB"},
    {"symbol": "XRP", "display_name": "XRP-PERP", "coin": "XRP"},
    {"symbol": "DOGE", "display_name": "DOGE-PERP", "coin": "DOGE"},
    {"symbol": "AVAX", "display_name": "AVAX-PERP", "coin": "AVAX"},
    {"symbol": "ARB", "display_name": "ARB-PERP", "coin": "ARB"},
    {"symbol": "OP", "display_name": "OP-PERP", "coin": "OP"},
    {"symbol": "WIF", "display_name": "WIF-PERP", "coin": "WIF"},
    {"symbol": "PEPE", "display_name": "PEPE-PERP", "coin": "kPEPE"},
    {"symbol": "SUI", "display_name": "SUI-PERP", "coin": "SUI"},
    {"symbol": "LINK", "display_name": "LINK-PERP", "coin": "LINK"},
    {"symbol": "AAVE", "display_name": "AAVE-PERP", "coin": "AAVE"},
    {"symbol": "FET", "display_name": "FET-PERP", "coin": "FET"},
]

HYPERLIQUID_API = "https://api.hyperliquid.xyz/info"


async def get_perpetual_symbols() -> list:
    """Return the curated list of Hyperliquid perpetual pairs."""
    return [
        {"symbol": p["symbol"], "display_name": p["display_name"], "coin": p["coin"]}
        for p in HYPERLIQUID_PERPS
    ]


async def get_info(symbol: str = "all") -> dict:
    """Fetch Hyperliquid market info via POST API."""
    async with httpx.AsyncClient() as client:
        payload = {"type": "allMids"}
        resp = await client.post(HYPERLIQUID_API, json=payload)
        resp.raise_for_status()
        data = resp.json()

    if symbol == "all":
        return data

    return {symbol: data.get(symbol, "")}


async def get_candles(symbol: str, interval: str = "1h", limit: int = 200) -> list:
    """
    Fetch historical candles for a Hyperliquid perpetual pair.
    Uses the public info API to get candlestick data.
    Returns list of dicts: {timestamp, open, high, low, close, volume}
    """
    # Map interval to Hyperliquid timeframe
    timeframe_map = {
        "5m": 300000,
        "15m": 900000,
        "1h": 3600000,
        "4h": 14400000,
        "1d": 86400000,
    }
    ms = timeframe_map.get(interval, 3600000)

    async with httpx.AsyncClient() as client:
        payload = {
            "type": "candle",
            "startTime": int(time.time() * 1000) - (limit * ms),
            "interval": ms,
            "coin": _coin_to_hyperliquid(symbol),
        }
        try:
            resp = await client.post(HYPERLIQUID_API, json=payload)
            resp.raise_for_status()
            raw = resp.json()

            candles = []
            for c in raw:
                candles.append({
                    "timestamp": datetime.fromtimestamp(c[0] / 1000, tz=timezone.utc),
                    "open": float(c[1]),
                    "high": float(c[2]),
                    "low": float(c[3]),
                    "close": float(c[4]),
                    "volume": float(c[5]),
                    "close_at": c[6],
                })
            return candles
        except Exception as e:
            logger.error(f"Failed to fetch candles for {symbol}: {e}")
            return []


def _coin_to_hyperliquid(symbol: str) -> str:
    """Map symbol to Hyperliquid coin name."""
    coin_map = {p["symbol"]: p["coin"] for p in HYPERLIQUID_PERPS}
    return coin_map.get(symbol, symbol)


# --- WebSocket streaming ---

async def subscribe_candles(symbol: str, interval: str = "1h", callback=None):
    """
    Subscribe to real-time candlestick data via Hyperliquid WebSocket.
    Yields candle updates.
    """
    url = "wss://api.hyperliquid.xyz"

    timeframe_map = {
        "5m": 300000, "15m": 900000, "1h": 3600000, "4h": 14400000, "1d": 86400000,
    }
    ms = timeframe_map.get(interval, 3600000)
    coin = _coin_to_hyperliquid(symbol)

    subscription = {
        "type": "candle",
        "interval": ms,
        "coin": coin,
    }

    reconnect_delay = 1
    max_reconnect = 30

    while True:
        try:
            async with websockets.connect(url) as ws:
                await ws.send(json.dumps({"type": "subscribe", "subscribe": subscription}))
                logger.info(f"Subscribed to {symbol} {interval} candles on Hyperliquid")

                while True:
                    msg = await ws.recv()
                    data = json.loads(msg)
                    if callback:
                        await callback(data, symbol, interval)
                    reconnect_delay = 1
        except Exception as e:
            logger.warning(f"WebSocket reconnecting {symbol} in {reconnect_delay}s: {e}")
            await asyncio.sleep(reconnect_delay)
            reconnect_delay = min(reconnect_delay * 2, max_reconnect)
