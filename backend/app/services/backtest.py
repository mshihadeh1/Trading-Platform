"""Backtest engine - replay strategies against historical data."""

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional

import pandas as pd
from app.services.indicators import compute_indicators

logger = logging.getLogger(__name__)


def evaluate_condition(indicator: str, operator: str, value: float, actual: float) -> bool:
    """Evaluate a single strategy condition."""
    if operator == "lt":
        return actual < value
    elif operator == "gt":
        return actual > value
    elif operator == "lte":
        return actual <= value
    elif operator == "gte":
        return actual >= value
    elif operator == "crosses_above":
        return actual > value
    elif operator == "crosses_below":
        return actual < value
    return False


def run_backtest(candles: List[dict], conditions: List[dict],
                  initial_capital: float = 10000, timeframe: str = "1h") -> Optional[dict]:
    """Run a backtest on historical candle data with strategy conditions."""
    if len(candles) < 50:
        return {"error": "Insufficient historical data (need 50+ candles)"}

    # Parse candles
    df = pd.DataFrame(candles)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp").reset_index(drop=True)

    capital = initial_capital
    positions = []
    open_position = None
    equity_curve = []
    trade_log = []

    for i in range(50, len(df)):
        # Get slice for indicator computation
        window = df.iloc[:i+1]
        indicators = compute_indicators(
            window[["timestamp", "open", "high", "low", "close", "volume"]].to_dict("records")
        )
        if not indicators:
            continue

        current_price = float(df.iloc[i]["close"])
        current_time = df.iloc[i]["timestamp"]

        # Check open position
        if open_position:
            # Check stop loss
            if open_position["side"] == "long":
                if current_price <= open_position["stop_loss"]:
                    pnl = (open_position["stop_loss"] - open_position["entry"]) * open_position["quantity"]
                    capital += pnl
                    positions.append({
                        "entry": open_position["entry"],
                        "exit": open_position["stop_loss"],
                        "side": open_position["side"],
                        "pnl": pnl,
                        "time": current_time,
                        "reason": "stop_loss",
                    })
                    trade_log.append({
                        "entry_time": open_position["time"].isoformat(),
                        "exit_time": current_time.isoformat(),
                        "entry": open_position["entry"],
                        "exit": open_position["stop_loss"],
                        "side": open_position["side"],
                        "pnl": round(pnl, 2),
                        "reason": "stop_loss",
                    })
                    open_position = None
                elif open_position.get("take_profit") and current_price >= open_position["take_profit"]:
                    pnl = (open_position["take_profit"] - open_position["entry"]) * open_position["quantity"]
                    capital += pnl
                    positions.append({
                        "entry": open_position["entry"],
                        "exit": open_position["take_profit"],
                        "side": open_position["side"],
                        "pnl": pnl,
                        "time": current_time,
                        "reason": "take_profit",
                    })
                    trade_log.append({
                        "entry_time": open_position["time"].isoformat(),
                        "exit_time": current_time.isoformat(),
                        "entry": open_position["entry"],
                        "exit": open_position["take_profit"],
                        "side": open_position["side"],
                        "pnl": round(pnl, 2),
                        "reason": "take_profit",
                    })
                    open_position = None
            else:  # short
                if current_price >= open_position["stop_loss"]:
                    pnl = (open_position["entry"] - open_position["stop_loss"]) * open_position["quantity"]
                    capital += pnl
                    positions.append({
                        "entry": open_position["entry"],
                        "exit": open_position["stop_loss"],
                        "side": open_position["side"],
                        "pnl": pnl,
                        "time": current_time,
                        "reason": "stop_loss",
                    })
                    open_position = None
                elif open_position.get("take_profit") and current_price <= open_position["take_profit"]:
                    pnl = (open_position["entry"] - open_position["take_profit"]) * open_position["quantity"]
                    capital += pnl
                    positions.append({
                        "entry": open_position["entry"],
                        "exit": open_position["take_profit"],
                        "side": open_position["side"],
                        "pnl": pnl,
                        "time": current_time,
                        "reason": "take_profit",
                    })
                    open_position = None

        # Check entry conditions
        if open_position is None:
            all_met = True
            for cond in conditions:
                ind_name = cond.get("indicator", "")
                op = cond.get("operator", "")
                val = cond.get("value", 0)
                actual = indicators.get(ind_name)
                if actual is None:
                    all_met = False
                    break
                if not evaluate_condition(ind_name, op, val, actual):
                    all_met = False
                    break

            if all_met and conditions:
                # Open position with stop loss 2% away and TP 4% away (2:1 R:R)
                if indicators.get("rsi") is not None:
                    if indicators["rsi"] < 50:
                        stop_loss = current_price * 0.98
                        take_profit = current_price * 1.04
                        side = "long"
                    else:
                        stop_loss = current_price * 1.02
                        take_profit = current_price * 0.96
                        side = "short"
                    quantity = (initial_capital * 0.1) / current_price  # 10% of capital
                    open_position = {
                        "entry": current_price,
                        "stop_loss": stop_loss,
                        "take_profit": take_profit,
                        "side": side,
                        "quantity": quantity,
                        "time": current_time,
                    }

        # Record equity
        unrealized = 0
        if open_position:
            if open_position["side"] == "long":
                unrealized = (current_price - open_position["entry"]) * open_position["quantity"]
            else:
                unrealized = (open_position["entry"] - current_price) * open_position["quantity"]
        equity_curve.append({
            "timestamp": current_time.isoformat(),
            "equity": capital + unrealized,
        })

    # Close any remaining open position at last price
    if open_position:
        last_price = float(df.iloc[-1]["close"])
        if open_position["side"] == "long":
            pnl = (last_price - open_position["entry"]) * open_position["quantity"]
        else:
            pnl = (open_position["entry"] - last_price) * open_position["quantity"]
        capital += pnl
        positions.append({
            "entry": open_position["entry"],
            "exit": last_price,
            "side": open_position["side"],
            "pnl": pnl,
            "time": df.iloc[-1]["timestamp"],
            "reason": "end_of_period",
        })
        trade_log.append({
            "entry_time": open_position["time"].isoformat(),
            "exit_time": df.iloc[-1]["timestamp"].isoformat(),
            "entry": open_position["entry"],
            "exit": last_price,
            "side": open_position["side"],
            "pnl": round(pnl, 2),
            "reason": "end_of_period",
        })

    # Calculate metrics
    wins = [p for p in positions if p["pnl"] > 0]
    losses = [p for p in positions if p["pnl"] <= 0]
    total_trades = len(positions)
    win_rate = (len(wins) / total_trades * 100) if total_trades > 0 else 0
    total_return = capital - initial_capital
    total_return_pct = (total_return / initial_capital * 100) if initial_capital else 0

    # Max drawdown
    equity_values = [e["equity"] for e in equity_curve]
    peak = equity_values[0] if equity_values else initial_capital
    max_dd = 0
    for eq in equity_values:
        if eq > peak:
            peak = eq
        dd = (peak - eq) / peak * 100 if peak > 0 else 0
        if dd > max_dd:
            max_dd = dd

    # Sharpe ratio (approximate)
    if len(equity_values) > 1:
        returns = pd.Series(equity_values).pct_change().dropna()
        sharpe = (returns.mean() / returns.std() * (252 ** 0.5)) if returns.std() > 0 else 0
    else:
        sharpe = 0

    # Sortino ratio
    if len(equity_values) > 1:
        downside = returns[returns < 0]
        downside_std = downside.std() if len(downside) > 0 else 1e-10
        sortino = (returns.mean() / downside_std * (252 ** 0.5)) if downside_std > 0 else 0
    else:
        sortino = 0

    # Profit factor
    gross_profit = sum(p["pnl"] for p in wins) if wins else 0
    gross_loss = abs(sum(p["pnl"] for p in losses)) if losses else 0
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else (999 if gross_profit > 0 else 0)

    avg_win = (sum(p["pnl"] for p in wins) / len(wins)) if wins else 0
    avg_loss = (sum(p["pnl"] for p in losses) / len(losses)) if losses else 0

    return {
        "total_trades": total_trades,
        "win_rate": round(win_rate, 2),
        "total_return": round(total_return, 2),
        "total_return_pct": round(total_return_pct, 2),
        "max_drawdown": round(max_dd, 2),
        "sharpe_ratio": round(sharpe, 2),
        "sortino_ratio": round(sortino, 2),
        "profit_factor": round(profit_factor, 2),
        "avg_win": round(avg_win, 2),
        "avg_loss": round(avg_loss, 2),
        "equity_curve": equity_curve,
        "trade_log": trade_log,
    }
