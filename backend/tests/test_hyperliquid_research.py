from datetime import datetime, timezone, timedelta
from pathlib import Path
import sys

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from services.hyperliquid_research.features import compute_crypto_features
from services.hyperliquid_research.market_audit import classify_market, score_market
from services.hyperliquid_research.paper_broker import PaperBroker, RiskConfig
from services.hyperliquid_research.strategies import trend_flow_signal


def _sample_candles(rows: int = 80, breakout: bool = True) -> pd.DataFrame:
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    data = []
    price = 100.0
    for i in range(rows):
        price += 0.25
        high = price + 0.4
        low = price - 0.4
        close = price + (1.0 if breakout and i == rows - 1 else 0.0)
        volume = 1000 + i * 5
        if i == rows - 1:
            volume = 2500
        data.append(
            {
                "timestamp": start + timedelta(minutes=15 * i),
                "open": price - 0.2,
                "high": high + (1.0 if breakout and i == rows - 1 else 0.0),
                "low": low,
                "close": close,
                "volume": volume,
            }
        )
    return pd.DataFrame(data)


def test_classifies_baseline_and_stock_like_markets():
    assert classify_market("BTC") == "crypto_major"
    assert classify_market("ETH") == "crypto_major"
    assert classify_market("SOL") == "crypto_major"
    assert classify_market("AAPL") == "stock_like"
    assert classify_market("SPX") == "index_like"
    assert classify_market("GOLD") == "commodity_like"
    assert classify_market("WIF") == "crypto_alt"


def test_market_score_rejects_missing_liquidity_tracking_data():
    scored = score_market(
        {
            "symbol": "AAPL",
            "mid_price": 200.0,
            "mark_price": None,
            "oracle_price": None,
            "volume_24h": None,
            "open_interest": None,
            "funding_rate": None,
            "spread_bps": None,
            "candle_count": 0,
            "trade_count": 0,
        }
    )

    assert scored["category"] == "stock_like"
    assert scored["tradable_candidate"] is False
    assert "insufficient" in scored["reject_reason"].lower()


def test_crypto_features_include_vwap_emas_returns_and_breakout():
    features = compute_crypto_features(_sample_candles())

    latest = features.iloc[-1]
    assert latest["vwap"] > 0
    assert latest["ema_9"] > latest["ema_20"] > latest["ema_50"]
    assert latest["return_15m"] > 0
    assert latest["volume_expansion"] is True or latest["volume_expansion"] == 1
    assert latest["range_breakout_15m"] is True or latest["range_breakout_15m"] == 1


def test_trend_flow_signal_logs_reasons_and_failed_checks():
    feature_frame = compute_crypto_features(_sample_candles())
    signal = trend_flow_signal("BTC", feature_frame, market_score={"funding_rate": 0.0001})

    assert signal["symbol"] == "BTC"
    assert signal["side"] in {"long", "short", "none"}
    assert isinstance(signal["reason"], list)
    assert isinstance(signal["failed_checks"], list)
    assert signal["suggested_stop"] is not None
    assert signal["suggested_take_profit"] is not None
    assert signal["suggested_max_hold_minutes"] > 0


def test_paper_broker_sizes_by_risk_and_records_skipped_signals():
    broker = PaperBroker(RiskConfig(initial_cash_usd=10000, max_risk_per_trade_pct=0.005, max_open_positions=1))
    signal = {
        "symbol": "BTC",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "side": "long",
        "confidence_score": 0.8,
        "suggested_stop": 99.0,
        "suggested_take_profit": 103.0,
        "suggested_max_hold_minutes": 60,
        "reason": ["test"],
        "failed_checks": [],
        "risk_notes": [],
    }

    entry = broker.process_signal(signal, mark_price=100.0)
    assert entry["event"] == "entry"
    assert round(entry["max_risk_usd"], 2) == 50.00
    assert entry["quantity"] > 0

    skipped = broker.process_signal({**signal, "symbol": "ETH"}, mark_price=2000.0)
    assert skipped["event"] == "skipped"
    assert "open position" in skipped["reason"].lower()
