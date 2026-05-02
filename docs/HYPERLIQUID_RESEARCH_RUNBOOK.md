# Hyperliquid Research Runbook

This module adds a Phase 1 research and paper-trading pipeline for Hyperliquid perps.

It does:
- Fetch public Hyperliquid market metadata, mids, asset contexts, candles, and recent trades where available.
- Classify markets as crypto_major, crypto_alt, stock_like, index_like, commodity_like, or unknown.
- Score market quality using liquidity, spread, data availability, tracking, and funding fields.
- Generate deterministic paper-only strategy signals.
- Simulate paper entries/exits with explicit stops, take profit, risk limits, and skipped-trade logs.
- Save CSV/JSON/JSONL outputs under data/hyperliquid.

It does NOT:
- Place live orders.
- Require private keys.
- Use leverage above 2x.
- Average down or martingale.
- Let an AI black box decide trades.
- Assume stock/index-like perps are liquid, safe, or profitable.

## First command to run

From the repo root:

```bash
python3 scripts/run_hyperliquid_market_audit.py --output data/hyperliquid/
```

Optional quick smoke:

```bash
python3 scripts/run_hyperliquid_market_audit.py --output data/hyperliquid/ --limit 10
```

Inspect:
- data/hyperliquid/market_audit_<timestamp>.csv
- data/hyperliquid/market_audit_<timestamp>.json

Focus on:
- tradable_candidate
- overall_score
- reject_reason
- volume_24h
- open_interest
- spread_bps
- mark_oracle_diff_bps
- candle_count
- trade_count

If liquidity/spread/tracking data is missing, the market is rejected. Missing data is not faked.

## Backtest / research replay

Crypto baseline:

```bash
python3 scripts/run_hyperliquid_backtest.py --symbols BTC,ETH,SOL --strategy trend_flow_baseline --output data/hyperliquid/backtest_latest
```

Stock/index placeholder, only after audit suggests candidates:

```bash
python3 scripts/run_hyperliquid_backtest.py --symbols AAPL,SPX,QQQ --strategy stock_index_placeholder --output data/hyperliquid/backtest_stock_placeholder
```

Outputs:
- trades.csv
- equity_curve.csv
- decisions.csv
- skipped_signals.csv
- metrics.json

## Forward paper test

Finite smoke test:

```bash
python3 scripts/run_hyperliquid_forward_paper.py --symbols BTC,ETH,SOL --iterations 3 --poll-seconds 30 --output data/hyperliquid/forward_paper
```

Continuous paper run:

```bash
python3 scripts/run_hyperliquid_forward_paper.py --symbols BTC,ETH,SOL --poll-seconds 60 --output data/hyperliquid/forward_paper
```

Outputs:
- forward_decisions.jsonl
- forward_events.jsonl

## Strategy notes

BTC/ETH/SOL trend-flow baseline requires deterministic checks around VWAP, EMA trend, 15m breakout/breakdown, volume expansion, funding sanity, and major-market regime placeholder.

Stock/index-like strategy is intentionally a placeholder. It requires market audit pass, U.S. market-hours awareness, VWAP/opening-range behavior, acceptable liquidity/tracking, and optional external underlying confirmation. The yfinance-backed underlying interface is isolated in services/hyperliquid_research/external_equity_data.py.

## Risk limits

Defaults:
- initial_cash_usd = 10000
- max_risk_per_trade_pct = 0.005
- max_daily_loss_pct = 0.02
- max_weekly_loss_pct = 0.05
- max_open_positions = 2
- leverage = 1.0
- max_leverage_allowed = 2.0
- max_trades_per_day = 2

No averaging down. No martingale. Every entry must have a stop and take-profit estimate.

## Known limitations

- Hyperliquid public fields may vary by market; missing fields are marked unavailable and can reject markets.
- Backtest runner is an MVP decision replay, not a full intrabar historical simulator yet.
- Funding history and robust open-interest history are placeholders unless Hyperliquid endpoints expose enough historical data.
- Stock/index underlying confirmation is isolated and best-effort through yfinance when available.
- U.S. market hours are approximated in Phase 1; DST/holiday calendars need a later upgrade.
- No Web UI has been added yet; this keeps the first research iteration auditable and script-first.

## Next steps before live trading

1. Run market audit for several sessions and compare stock/index-like candidates with crypto majors.
2. Reject markets with missing liquidity/spread/tracking data.
3. Improve historical backtest fidelity, fees, slippage, and funding estimates.
4. Add benchmark comparisons and richer metrics.
5. Add friendly Web UI only after audit outputs are trusted.
6. Add a live execution adapter only after a paper strategy survives forward testing and separate risk review.
