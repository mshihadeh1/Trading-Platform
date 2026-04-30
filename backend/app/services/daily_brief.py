"""Daily market brief generation."""

import json
from datetime import date
from typing import Any

from sqlmodel import Session, select

from app.models.candle import Candle
from app.models.daily_brief import DailyBrief, DailyBriefResponse
from app.models.paper_trade import PaperTrade
from app.models.signal import Signal
from app.models.symbol import Symbol
from app.utils.time import utc_now

VALID_REGIMES = {"bullish", "bearish", "choppy", "risk-off", "risk-on", "mixed"}


class DailyBriefService:
    """Generate deterministic daily briefs from latest signals, candles, and paper positions."""

    def generate(self, db: Session, brief_date: date | None = None) -> DailyBrief:
        brief_date = brief_date or utc_now().date()
        watchlist = list(db.exec(select(Symbol).where(Symbol.is_active == True).order_by(Symbol.exchange, Symbol.symbol)).all())
        latest_signals = self._latest_signals_by_symbol(db)
        latest_candles = self._latest_candles_by_symbol(db)
        open_trades = list(db.exec(select(PaperTrade).where(PaperTrade.status == "open")).all())

        opportunities = self._top_opportunities(watchlist, latest_signals)
        regime = self._infer_market_regime(latest_signals.values())
        summary = self._build_summary(watchlist, opportunities, regime)
        risk_summary = self._open_positions_summary(open_trades)
        watchlist_snapshot = self._watchlist_snapshot(watchlist, latest_signals, latest_candles)
        risk_notes = self._risk_notes(risk_summary, opportunities)

        brief = DailyBrief(
            brief_date=brief_date,
            market_regime=regime,
            summary=summary,
            top_opportunities_json=json.dumps(opportunities),
            risk_notes=risk_notes,
            open_positions_summary_json=json.dumps(risk_summary),
            watchlist_snapshot_json=json.dumps(watchlist_snapshot),
            llm_reasoning="Deterministic brief generated from latest stored signals, candles, and paper positions.",
            created_at=utc_now(),
        )
        db.add(brief)
        db.commit()
        db.refresh(brief)
        return brief

    def latest(self, db: Session) -> DailyBrief | None:
        return db.exec(select(DailyBrief).order_by(DailyBrief.created_at.desc()).limit(1)).first()

    def history(self, db: Session, limit: int = 20) -> list[DailyBrief]:
        return list(db.exec(select(DailyBrief).order_by(DailyBrief.created_at.desc()).limit(limit)).all())

    def to_response(self, brief: DailyBrief) -> DailyBriefResponse:
        return DailyBriefResponse(
            id=brief.id or 0,
            brief_date=brief.brief_date,
            market_regime=brief.market_regime,
            summary=brief.summary,
            top_opportunities=self._loads(brief.top_opportunities_json, []),
            risk_notes=brief.risk_notes,
            open_positions_summary=self._loads(brief.open_positions_summary_json, {}),
            watchlist_snapshot=self._loads(brief.watchlist_snapshot_json, []),
            llm_reasoning=brief.llm_reasoning,
            created_at=brief.created_at,
        )

    def _latest_signals_by_symbol(self, db: Session) -> dict[int, Signal]:
        signals = db.exec(select(Signal).order_by(Signal.timestamp.desc())).all()
        latest: dict[int, Signal] = {}
        for signal in signals:
            if signal.symbol_id is not None and signal.symbol_id not in latest:
                latest[signal.symbol_id] = signal
        return latest

    def _latest_candles_by_symbol(self, db: Session) -> dict[int, Candle]:
        candles = db.exec(select(Candle).order_by(Candle.timestamp.desc())).all()
        latest: dict[int, Candle] = {}
        for candle in candles:
            if candle.symbol_id is not None and candle.symbol_id not in latest:
                latest[candle.symbol_id] = candle
        return latest

    def _top_opportunities(self, watchlist: list[Symbol], latest_signals: dict[int, Signal]) -> list[dict[str, Any]]:
        rows = []
        for symbol in watchlist:
            signal = latest_signals.get(symbol.symbol_id or -1)
            if not signal or signal.direction not in {"buy", "sell"}:
                continue
            rows.append(
                {
                    "symbol": symbol.symbol,
                    "display_name": symbol.display_name,
                    "exchange": symbol.exchange,
                    "direction": signal.direction,
                    "confidence": signal.confidence,
                    "setup_type": signal.setup_type,
                    "time_horizon": signal.time_horizon,
                    "entry_price": signal.entry_price,
                    "entry_min": signal.entry_min,
                    "entry_max": signal.entry_max,
                    "stop_loss": signal.stop_loss,
                    "take_profit": signal.take_profit,
                    "take_profit_2": signal.take_profit_2,
                    "risk_reward": signal.risk_reward,
                    "invalidation": signal.invalidation,
                    "reasoning": signal.reasoning,
                    "signal_id": signal.id,
                    "timestamp": signal.timestamp.isoformat() if signal.timestamp else None,
                }
            )
        return sorted(rows, key=lambda row: (row.get("confidence") or 0, row.get("risk_reward") or 0), reverse=True)[:5]

    def _infer_market_regime(self, signals) -> str:
        signals = list(signals)
        actionable = [signal for signal in signals if signal.direction in {"buy", "sell"} and signal.confidence >= 60]
        if not actionable:
            return "mixed" if signals else "choppy"
        buys = sum(1 for signal in actionable if signal.direction == "buy")
        sells = sum(1 for signal in actionable if signal.direction == "sell")
        if buys >= max(2, sells * 2):
            return "risk-on"
        if sells >= max(2, buys * 2):
            return "risk-off"
        return "mixed"

    def _build_summary(self, watchlist: list[Symbol], opportunities: list[dict[str, Any]], regime: str) -> str:
        if opportunities:
            leaders = ", ".join(f"{row['symbol']} {row['direction']} ({row['confidence']}%)" for row in opportunities[:3])
            return f"{regime.title()} morning scan across {len(watchlist)} symbols. Top focus: {leaders}."
        if watchlist:
            return f"{regime.title()} morning scan across {len(watchlist)} symbols. No high-confidence actionable setups yet."
        return "No active watchlist symbols. Add symbols to generate a useful daily brief."

    def _open_positions_summary(self, trades: list[PaperTrade]) -> dict[str, Any]:
        exposure = sum((trade.entry_price or 0) * (trade.quantity or 0) for trade in trades)
        unrealized = sum(trade.pnl or 0 for trade in trades)
        return {
            "open_positions": len(trades),
            "notional_exposure": round(exposure, 2),
            "unrealized_pnl": round(unrealized, 2),
            "symbols": [trade.symbol_id for trade in trades],
        }

    def _watchlist_snapshot(
        self,
        watchlist: list[Symbol],
        latest_signals: dict[int, Signal],
        latest_candles: dict[int, Candle],
    ) -> list[dict[str, Any]]:
        snapshot = []
        for symbol in watchlist:
            signal = latest_signals.get(symbol.symbol_id or -1)
            candle = latest_candles.get(symbol.symbol_id or -1)
            snapshot.append(
                {
                    "symbol_id": symbol.symbol_id,
                    "symbol": symbol.symbol,
                    "display_name": symbol.display_name,
                    "exchange": symbol.exchange,
                    "latest_price": candle.close if candle else None,
                    "latest_candle_at": candle.timestamp.isoformat() if candle and candle.timestamp else None,
                    "direction": signal.direction if signal else "none",
                    "confidence": signal.confidence if signal else None,
                    "setup_type": signal.setup_type if signal else None,
                }
            )
        return snapshot

    def _risk_notes(self, risk_summary: dict[str, Any], opportunities: list[dict[str, Any]]) -> str:
        notes = []
        if risk_summary["open_positions"]:
            notes.append(f"{risk_summary['open_positions']} paper position(s) currently open.")
        else:
            notes.append("No open paper positions.")
        missing_risk = [row["symbol"] for row in opportunities if not row.get("stop_loss") or not row.get("take_profit")]
        if missing_risk:
            notes.append(f"Avoid acting on setups missing stops/targets: {', '.join(missing_risk)}.")
        return " ".join(notes)

    def _loads(self, value: str, default):
        try:
            return json.loads(value or "")
        except (TypeError, json.JSONDecodeError):
            return default
