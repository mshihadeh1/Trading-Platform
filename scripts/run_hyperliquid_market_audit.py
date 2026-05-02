#!/usr/bin/env python3
"""Run Hyperliquid public-market audit and save CSV/JSON outputs."""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.hyperliquid_research.hyperliquid_client import HyperliquidPublicClient
from services.hyperliquid_research.market_audit import classify_market, save_audit, score_market


async def run(output: str, limit: int | None = None) -> None:
    client = HyperliquidPublicClient()
    markets = await client.fetch_universe()
    contexts = await client.fetch_asset_contexts()
    mids = await client.fetch_all_mids()
    rows = []
    selected = markets[:limit] if limit else markets
    for market in selected:
        symbol = market["symbol"]
        context = {**market, **contexts.get(symbol, {})}
        if context.get("mid_price") is None and symbol in mids:
            context["mid_price"] = mids[symbol]
        candles = await client.fetch_candles(symbol, interval="15m", limit=120)
        trades = await client.fetch_recent_trades(symbol)
        context["candle_count"] = len(candles)
        context["trade_count"] = len(trades)
        rows.append(score_market(context))
    csv_path, json_path = save_audit(rows, output)
    print(f"Saved audit CSV: {csv_path}")
    print(f"Saved audit JSON: {json_path}")
    for category in ["crypto_major", "stock_like", "index_like", "crypto_alt", "commodity_like", "unknown"]:
        top = sorted([r for r in rows if r["category"] == category], key=lambda r: r["overall_score"], reverse=True)[:8]
        if not top:
            continue
        print(f"\nTop {category} candidates:")
        for row in top:
            status = "TRADE-CANDIDATE" if row["tradable_candidate"] else "reject"
            print(f"  {row['symbol']:>10} score={row['overall_score']:.2f} {status} reason={row['reject_reason'] or '-'}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit Hyperliquid market quality for research/paper trading")
    parser.add_argument("--output", default="data/hyperliquid/", help="Output directory for market_audit timestamped CSV/JSON")
    parser.add_argument("--limit", type=int, default=None, help="Optional market limit for quick smoke tests")
    args = parser.parse_args()
    asyncio.run(run(args.output, args.limit))


if __name__ == "__main__":
    main()
