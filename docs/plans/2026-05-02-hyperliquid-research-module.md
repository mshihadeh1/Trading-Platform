# Hyperliquid Research Module Implementation Plan

> For Hermes: Use the trading-platform-development and test-driven-development skills when executing this plan.

Goal: Add a paper-only Hyperliquid research pipeline that audits market quality before any strategy or execution assumptions.

Architecture: Keep the research package separate from the FastAPI app under services/hyperliquid_research. Scripts call the package and write CSV/JSON outputs under data/hyperliquid. The existing Web UI should only receive this later after the CLI pipeline is reliable.

Tech Stack: Python, httpx, pandas, yfinance placeholder, pytest, CSV/JSON outputs.

Tasks:
1. Add failing tests for market classification, audit rejection, features, deterministic signals, and paper broker risk sizing.
2. Create services/hyperliquid_research/hyperliquid_client.py for public API data only.
3. Create market_audit.py with category classification, score fields, reject reasons, and CSV/JSON saving.
4. Create features.py with crypto and stock/index feature frames.
5. Create external_equity_data.py as isolated underlying quote/candle interface.
6. Create strategies.py with BTC/ETH/SOL trend-flow and stock/index placeholder signals.
7. Create paper_broker.py with no live trading, max 2x leverage, stops, TP, loss/trade caps, and skip logging.
8. Create scripts for audit, backtest, and forward paper mode.
9. Add configs/hyperliquid_research.yaml.
10. Add docs/HYPERLIQUID_RESEARCH_RUNBOOK.md and update README.
11. Verify backend tests, compile, frontend build if UI/README touched, docker compose config.

UI policy: Do not add complex Web UI until market_audit output is useful. Later, add a friendly Research tab showing top candidates, why rejected, and clear paper-only status.
