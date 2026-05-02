"""Market discovery, classification, and quality scoring."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

CRYPTO_MAJORS = {"BTC", "ETH", "SOL"}
INDEX_LIKE = {"SPX", "SPY", "QQQ", "NDX", "NASDAQ", "DOW", "DJI", "IWM", "RUT"}
COMMODITY_LIKE = {"GOLD", "XAU", "SILVER", "XAG", "OIL", "WTI", "BRENT"}
STOCK_LIKE = {
    "AAPL", "MSFT", "NVDA", "TSLA", "META", "AMZN", "GOOGL", "GOOG", "NFLX",
    "COIN", "MSTR", "AMD", "INTC", "BABA", "PLTR", "SMCI", "AVGO", "HOOD",
}
KNOWN_CRYPTO_ALTS = {
    "BNB", "XRP", "DOGE", "AVAX", "ARB", "OP", "WIF", "PEPE", "kPEPE", "SUI", "LINK",
    "AAVE", "FET", "UNI", "LTC", "BCH", "DOT", "APT", "SEI", "TIA", "INJ", "NEAR",
}


def classify_market(symbol: str) -> str:
    normalized = symbol.upper().replace("-PERP", "")
    if normalized in CRYPTO_MAJORS:
        return "crypto_major"
    if normalized in INDEX_LIKE:
        return "index_like"
    if normalized in COMMODITY_LIKE:
        return "commodity_like"
    if normalized in STOCK_LIKE:
        return "stock_like"
    if normalized in {s.upper() for s in KNOWN_CRYPTO_ALTS}:
        return "crypto_alt"
    if normalized.startswith("U") and normalized[1:] in STOCK_LIKE:
        return "stock_like"
    return "unknown"


def score_market(market: dict[str, Any], thresholds: dict[str, Any] | None = None) -> dict[str, Any]:
    thresholds = thresholds or {}
    symbol = str(market.get("symbol") or market.get("coin") or "")
    category = classify_market(symbol)
    volume = _float(market.get("volume_24h"))
    oi = _float(market.get("open_interest"))
    funding = _float(market.get("funding_rate"))
    mark = _float(market.get("mark_price"))
    oracle = _float(market.get("oracle_price"))
    mid = _float(market.get("mid_price")) or mark
    spread_bps = _spread_bps(market)
    candle_count = int(market.get("candle_count") or 0)
    trade_count = int(market.get("trade_count") or 0)

    liquidity_score = _score_threshold(volume, thresholds.get("good_volume_24h", 10_000_000), thresholds.get("min_volume_24h", 1_000_000))
    oi_score = _score_threshold(oi, thresholds.get("good_open_interest", 5_000_000), thresholds.get("min_open_interest", 500_000))
    spread_score = _inverse_score(spread_bps, thresholds.get("good_spread_bps", 5), thresholds.get("max_spread_bps", 25))
    data_score = min(1.0, (candle_count / 100.0) * 0.7 + (trade_count / 100.0) * 0.3)
    tracking_bps = abs((mark - oracle) / oracle * 10_000) if mark and oracle else None
    tracking_score = _inverse_score(tracking_bps, thresholds.get("good_tracking_bps", 10), thresholds.get("max_tracking_bps", 75))
    funding_score = _inverse_score(abs(funding * 10_000) if funding is not None else None, thresholds.get("good_abs_funding_bps", 2), thresholds.get("max_abs_funding_bps", 20))

    overall = (
        liquidity_score * 0.25
        + oi_score * 0.15
        + spread_score * 0.20
        + data_score * 0.20
        + tracking_score * 0.15
        + funding_score * 0.05
    )
    reject_reasons = []
    if category == "unknown":
        reject_reasons.append("unknown category")
    if volume is None or oi is None:
        reject_reasons.append("insufficient liquidity/open interest data")
    if spread_bps is None:
        reject_reasons.append("insufficient spread data")
    if mark is None or oracle is None:
        reject_reasons.append("insufficient tracking data")
    if candle_count < thresholds.get("min_candles", 20):
        reject_reasons.append("insufficient candle data")
    if overall < thresholds.get("min_overall_score", 0.60):
        reject_reasons.append("overall score below threshold")

    tradable = not reject_reasons
    return {
        "symbol": symbol,
        "category": category,
        "tradable_candidate": tradable,
        "liquidity_score": round(liquidity_score, 4),
        "spread_score": round(spread_score, 4),
        "data_score": round(data_score, 4),
        "tracking_score": round(tracking_score, 4),
        "funding_score": round(funding_score, 4),
        "overall_score": round(overall, 4),
        "reject_reason": "; ".join(dict.fromkeys(reject_reasons)),
        "mid_price": mid,
        "mark_price": mark,
        "oracle_price": oracle,
        "mark_oracle_diff_bps": round(tracking_bps, 4) if tracking_bps is not None else None,
        "spread_bps": round(spread_bps, 4) if spread_bps is not None else None,
        "volume_24h": volume,
        "open_interest": oi,
        "funding_rate": funding,
        "candle_count": candle_count,
        "trade_count": trade_count,
    }


def save_audit(rows: list[dict[str, Any]], output_dir: str | Path) -> tuple[Path, Path]:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    csv_path = out / f"market_audit_{stamp}.csv"
    json_path = out / f"market_audit_{stamp}.json"
    pd.DataFrame(rows).to_csv(csv_path, index=False)
    json_path.write_text(json.dumps(rows, indent=2, default=str), encoding="utf-8")
    return csv_path, json_path


def _spread_bps(market: dict[str, Any]) -> float | None:
    if market.get("spread_bps") is not None:
        return _float(market.get("spread_bps"))
    bid = _float(market.get("best_bid") or market.get("impact_bid"))
    ask = _float(market.get("best_ask") or market.get("impact_ask"))
    mid = _float(market.get("mid_price") or market.get("mark_price"))
    if bid and ask and mid:
        return max(0.0, (ask - bid) / mid * 10_000)
    return None


def _score_threshold(value: float | None, good: float, minimum: float) -> float:
    if value is None or value <= 0:
        return 0.0
    if value >= good:
        return 1.0
    if value <= minimum:
        return 0.25 * (value / minimum)
    return 0.25 + 0.75 * ((value - minimum) / (good - minimum))


def _inverse_score(value: float | None, good: float, maximum: float) -> float:
    if value is None:
        return 0.0
    if value <= good:
        return 1.0
    if value >= maximum:
        return 0.0
    return 1.0 - ((value - good) / (maximum - good))


def _float(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None
