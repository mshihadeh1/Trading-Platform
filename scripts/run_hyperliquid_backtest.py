#!/usr/bin/env python3
"""Simple Phase 1 Hyperliquid research backtest runner."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.hyperliquid_research.features import compute_crypto_features, compute_stock_like_features
from services.hyperliquid_research.hyperliquid_client import HyperliquidPublicClient
from services.hyperliquid_research.market_audit import score_market
from services.hyperliquid_research.paper_broker import PaperBroker, RiskConfig
from services.hyperliquid_research.strategies import stock_index_placeholder_signal, trend_flow_signal


async def run(symbols: list[str], strategy: str, output: str, interval: str, limit: int) -> None:
    out = Path(output)
    out.mkdir(parents=True, exist_ok=True)
    client = HyperliquidPublicClient()
    contexts = await client.fetch_asset_contexts()
    broker = PaperBroker(RiskConfig())
    decisions = []
    for symbol in symbols:
        candles = await client.fetch_candles(symbol, interval=interval, limit=limit)
        if candles.empty:
            decisions.append({"symbol": symbol, "side": "none", "failed_checks": ["no candles returned"]})
            continue
        context = {"symbol": symbol, **contexts.get(symbol, {}), "candle_count": len(candles), "trade_count": 0}
        audit = score_market(context)
        if strategy == "stock_index_placeholder":
            features = compute_stock_like_features(candles, audit)
            signal = stock_index_placeholder_signal(symbol, features, audit)
        else:
            features = compute_crypto_features(candles, market_context=audit)
            signal = trend_flow_signal(symbol, features, audit)
        decisions.append(signal)
        mark = float(candles.iloc[-1]["close"])
        broker.process_signal(signal, mark)
    trades = [e for e in broker.events if e.get("event") in {"entry", "exit"}]
    skipped = [e for e in broker.events if e.get("event") == "skipped"]
    pd.DataFrame(decisions).to_csv(out / "decisions.csv", index=False)
    pd.DataFrame(trades).to_csv(out / "trades.csv", index=False)
    pd.DataFrame(skipped).to_csv(out / "skipped_signals.csv", index=False)
    pd.DataFrame([{"timestamp": pd.Timestamp.now(tz="UTC").isoformat(), "equity": broker.cash}]).to_csv(out / "equity_curve.csv", index=False)
    metrics = {
        "initial_cash": broker.config.initial_cash_usd,
        "ending_cash": broker.cash,
        "total_return": (broker.cash / broker.config.initial_cash_usd) - 1,
        "number_of_trades": len(trades),
        "open_positions": len(broker.positions),
        "fees_funding_estimate_note": "fees estimated on paper entries/exits; funding placeholder is 0 until historical funding integration",
    }
    (out / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(f"Wrote backtest outputs to {out}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Phase 1 paper-only Hyperliquid research backtest")
    parser.add_argument("--symbols", default="BTC,ETH,SOL")
    parser.add_argument("--strategy", default="trend_flow_baseline", choices=["trend_flow_baseline", "stock_index_placeholder"])
    parser.add_argument("--interval", default="15m")
    parser.add_argument("--limit", type=int, default=250)
    parser.add_argument("--output", default="data/hyperliquid/backtest_latest")
    args = parser.parse_args()
    asyncio.run(run([s.strip() for s in args.symbols.split(",") if s.strip()], args.strategy, args.output, args.interval, args.limit))


if __name__ == "__main__":
    main()
