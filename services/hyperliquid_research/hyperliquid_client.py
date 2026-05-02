"""Public Hyperliquid market-data client for research workflows.

No private keys. No order placement. All methods fail soft and return normalized
plain Python objects or pandas DataFrames so audit/backtest scripts can continue
when one endpoint is unavailable.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable

import httpx
import pandas as pd

LOGGER = logging.getLogger(__name__)
INFO_URL = "https://api.hyperliquid.xyz/info"

INTERVAL_MS = {
    "1m": 60_000,
    "3m": 180_000,
    "5m": 300_000,
    "15m": 900_000,
    "30m": 1_800_000,
    "1h": 3_600_000,
    "4h": 14_400_000,
    "1d": 86_400_000,
}


@dataclass(slots=True)
class HyperliquidMarket:
    symbol: str
    coin: str
    sz_decimals: int | None = None
    max_leverage: float | None = None
    only_isolated: bool | None = None
    raw: dict[str, Any] | None = None


class HyperliquidPublicClient:
    """Small async client for Hyperliquid's public info API."""

    def __init__(self, info_url: str = INFO_URL, timeout: float = 15.0) -> None:
        self.info_url = info_url
        self.timeout = timeout

    async def _post(self, payload: dict[str, Any]) -> Any:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(self.info_url, json=payload)
                response.raise_for_status()
                return response.json()
        except Exception as exc:  # pragma: no cover - exact network failures vary
            LOGGER.warning("Hyperliquid request failed payload=%s error=%s", payload, exc)
            return None

    async def fetch_universe(self) -> list[dict[str, Any]]:
        """Fetch perp metadata/universe."""
        data = await self._post({"type": "meta"})
        universe = data.get("universe", []) if isinstance(data, dict) else []
        markets: list[dict[str, Any]] = []
        for item in universe:
            if not isinstance(item, dict) or not item.get("name"):
                continue
            markets.append(
                {
                    "symbol": item["name"],
                    "coin": item["name"],
                    "sz_decimals": item.get("szDecimals"),
                    "max_leverage": _safe_float(item.get("maxLeverage")),
                    "only_isolated": item.get("onlyIsolated"),
                    "raw": item,
                }
            )
        return markets

    async def fetch_asset_contexts(self) -> dict[str, dict[str, Any]]:
        """Fetch metadata plus per-asset context when available.

        Hyperliquid returns [meta, assetCtxs]. The exact fields can evolve, so this
        method normalizes common liquidity/tracking fields while preserving raw.
        """
        data = await self._post({"type": "metaAndAssetCtxs"})
        if not (isinstance(data, list) and len(data) >= 2):
            return {}
        universe = data[0].get("universe", []) if isinstance(data[0], dict) else []
        ctxs = data[1] if isinstance(data[1], list) else []
        result: dict[str, dict[str, Any]] = {}
        for meta, ctx in zip(universe, ctxs):
            if not isinstance(meta, dict) or not isinstance(ctx, dict):
                continue
            symbol = meta.get("name")
            if not symbol:
                continue
            mark = _safe_float(ctx.get("markPx") or ctx.get("markPrice"))
            oracle = _safe_float(ctx.get("oraclePx") or ctx.get("oraclePrice"))
            mid = _safe_float(ctx.get("midPx") or ctx.get("mid"))
            result[symbol] = {
                "symbol": symbol,
                "coin": symbol,
                "mark_price": mark,
                "oracle_price": oracle,
                "mid_price": mid or mark,
                "open_interest": _safe_float(ctx.get("openInterest")),
                "volume_24h": _safe_float(ctx.get("dayNtlVlm") or ctx.get("dayBaseVlm")),
                "funding_rate": _safe_float(ctx.get("funding")),
                "premium": _safe_float(ctx.get("premium")),
                "impact_bid": _safe_float(ctx.get("impactPxs", [None, None])[0]) if isinstance(ctx.get("impactPxs"), list) else None,
                "impact_ask": _safe_float(ctx.get("impactPxs", [None, None])[1]) if isinstance(ctx.get("impactPxs"), list) else None,
                "raw_context": ctx,
                "raw_meta": meta,
            }
        return result

    async def fetch_all_mids(self) -> dict[str, float]:
        data = await self._post({"type": "allMids"})
        if not isinstance(data, dict):
            return {}
        return {str(k): v for k, v in ((_k, _safe_float(_v)) for _k, _v in data.items()) if v is not None}

    async def fetch_candles(
        self,
        symbol: str,
        interval: str = "15m",
        start_ms: int | None = None,
        end_ms: int | None = None,
        limit: int = 500,
    ) -> pd.DataFrame:
        interval_ms = INTERVAL_MS.get(interval, INTERVAL_MS["15m"])
        end_ms = end_ms or int(time.time() * 1000)
        start_ms = start_ms or end_ms - (limit * interval_ms)
        payload = {
            "type": "candleSnapshot",
            "req": {"coin": symbol, "interval": interval, "startTime": start_ms, "endTime": end_ms},
        }
        data = await self._post(payload)
        if not isinstance(data, list):
            return _empty_candles()
        rows = []
        for item in data:
            try:
                if isinstance(item, dict):
                    ts = int(item.get("t"))
                    row = {
                        "timestamp": datetime.fromtimestamp(ts / 1000, tz=timezone.utc),
                        "open": float(item.get("o")),
                        "high": float(item.get("h")),
                        "low": float(item.get("l")),
                        "close": float(item.get("c")),
                        "volume": float(item.get("v", 0)),
                    }
                else:
                    ts = int(item[0])
                    row = {
                        "timestamp": datetime.fromtimestamp(ts / 1000, tz=timezone.utc),
                        "open": float(item[1]),
                        "high": float(item[2]),
                        "low": float(item[3]),
                        "close": float(item[4]),
                        "volume": float(item[5]),
                    }
                rows.append(row)
            except Exception:
                continue
        if not rows:
            return _empty_candles()
        return pd.DataFrame(rows).sort_values("timestamp").reset_index(drop=True)

    async def fetch_recent_trades(self, symbol: str) -> pd.DataFrame:
        data = await self._post({"type": "recentTrades", "coin": symbol})
        if not isinstance(data, list):
            return pd.DataFrame(columns=["timestamp", "price", "size", "side", "raw"])
        rows = []
        for item in data:
            if not isinstance(item, dict):
                continue
            ts = _safe_float(item.get("time") or item.get("t"))
            rows.append(
                {
                    "timestamp": datetime.fromtimestamp((ts or 0) / 1000, tz=timezone.utc) if ts else None,
                    "price": _safe_float(item.get("px") or item.get("price")),
                    "size": _safe_float(item.get("sz") or item.get("size")),
                    "side": item.get("side") or item.get("dir"),
                    "raw": item,
                }
            )
        return pd.DataFrame(rows)


def _empty_candles() -> pd.DataFrame:
    return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])


def _safe_float(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None
