#!/usr/bin/env python3
"""Forward paper runner. Public data only; no private keys; no live orders."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.hyperliquid_research.features import compute_crypto_features
from services.hyperliquid_research.hyperliquid_client import HyperliquidPublicClient
from services.hyperliquid_research.market_audit import score_market
from services.hyperliquid_research.paper_broker import PaperBroker, RiskConfig
from services.hyperliquid_research.strategies import trend_flow_signal


async def run(symbols: list[str], output: str, interval: str, poll_seconds: int, iterations: int | None) -> None:
    out = Path(output)
    out.mkdir(parents=True, exist_ok=True)
    client = HyperliquidPublicClient()
    broker = PaperBroker(RiskConfig())
    decisions_path = out / "forward_decisions.jsonl"
    trades_path = out / "forward_events.jsonl"
    count = 0
    print("Forward paper mode only. No private keys. No live orders.")
    while iterations is None or count < iterations:
        contexts = await client.fetch_asset_contexts()
        for symbol in symbols:
            candles = await client.fetch_candles(symbol, interval=interval, limit=120)
            if candles.empty:
                signal = {"symbol": symbol, "side": "none", "failed_checks": ["no candles returned"]}
                decisions_path.open("a", encoding="utf-8").write(json.dumps(signal, default=str) + "\n")
                continue
            audit = score_market({"symbol": symbol, **contexts.get(symbol, {}), "candle_count": len(candles), "trade_count": 0})
            features = compute_crypto_features(candles, market_context=audit)
            signal = trend_flow_signal(symbol, features, audit)
            mark = float(candles.iloc[-1]["close"])
            event = broker.mark_to_market(symbol, mark) or broker.process_signal(signal, mark)
            decisions_path.open("a", encoding="utf-8").write(json.dumps(signal, default=str) + "\n")
            trades_path.open("a", encoding="utf-8").write(json.dumps(event, default=str) + "\n")
            print(f"{symbol}: signal={signal.get('side')} confidence={signal.get('confidence_score')} event={event.get('event')}")
        print(f"Paper cash={broker.cash:.2f} open_positions={len(broker.positions)}")
        count += 1
        if iterations is not None and count >= iterations:
            break
        await asyncio.sleep(poll_seconds)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run forward paper-only Hyperliquid strategy simulation")
    parser.add_argument("--symbols", default="BTC,ETH,SOL")
    parser.add_argument("--interval", default="15m")
    parser.add_argument("--poll-seconds", type=int, default=60)
    parser.add_argument("--iterations", type=int, default=None, help="Optional finite loop count for testing")
    parser.add_argument("--output", default="data/hyperliquid/forward_paper")
    args = parser.parse_args()
    asyncio.run(run([s.strip() for s in args.symbols.split(",") if s.strip()], args.output, args.interval, args.poll_seconds, args.iterations))


if __name__ == "__main__":
    main()
