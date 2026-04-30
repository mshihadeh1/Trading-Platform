"""LLM-driven market analysis and signal persistence."""

import asyncio
import inspect
import json
import logging
from datetime import datetime
from app.utils.time import utc_now
from typing import Any, Optional

from openai import AsyncOpenAI
from sqlmodel import Session, select

from app.config import settings
from app.models.candle import Candle
from app.models.paper_trade import PaperTrade
from app.models.signal import Signal
from app.models.symbol import Symbol
from app.services.indicators import compute

logger = logging.getLogger(__name__)

ANALYSIS_PROMPT = """You are an expert quantitative trader. Analyze the following market data and provide trading recommendations.

Market: {symbol} on {exchange} ({timeframe})
Current Price: {price}
24h Change: {change_24h}%

Technical Indicators:
{indicators}

Price Action:
{price_action}

Volume Analysis:
{volume_analysis}

Rules:
- Provide clear entry, stop-loss, and take-profit levels
- Return hold when setup quality is weak
- Keep prices realistic for the current market
- Be specific with reasoning and reference the indicators

Return ONLY valid JSON:
{{
  "direction": "buy | sell | hold",
  "confidence": int,
  "setup_type": "breakout | pullback | mean_reversion | trend_continuation | reversal | none",
  "time_horizon": "scalp | intraday | swing",
  "entry_min": float | null,
  "entry_max": float | null,
  "entry_price": float | null,
  "stop_loss": float | null,
  "take_profit": float | null,
  "take_profit_2": float | null,
  "risk_reward": float | null,
  "invalidation": "what would invalidate this setup",
  "reasoning": "detailed explanation"
}}
"""


class LLMAnalysisService:
    """Build prompts, call the external LLM, and persist signals."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout_seconds: float = 15.0,
    ):
        self.base_url = base_url or settings.llm_base_url
        self.api_key = api_key or settings.llm_api_key
        self.model = model or settings.llm_model
        self.timeout_seconds = timeout_seconds

    def _create_client(self) -> AsyncOpenAI:
        return AsyncOpenAI(
            base_url=self.base_url,
            api_key=self.api_key,
            timeout=self.timeout_seconds,
        )

    async def _close_client(self, client: AsyncOpenAI) -> None:
        close = getattr(client, "close", None) or getattr(client, "aclose", None)
        if close is None:
            return
        result = close()
        if inspect.isawaitable(result):
            await result

    async def analyze(
        self,
        symbol: str,
        exchange: str,
        timeframe: str,
        price: float,
        change_24h: float,
        indicators: dict[str, Any],
        price_action: str,
        volume_analysis: str,
    ) -> Optional[dict[str, Any]]:
        indicators_str = "\n".join(
            f"- {key}: {value}" for key, value in indicators.items() if key != "price_action_summary"
        )
        prompt = ANALYSIS_PROMPT.format(
            symbol=symbol,
            exchange=exchange,
            timeframe=timeframe,
            price=round(price, 6),
            change_24h=round(change_24h, 2),
            indicators=indicators_str,
            price_action=price_action,
            volume_analysis=volume_analysis,
        )

        client = self._create_client()
        try:
            for attempt in range(3):
                try:
                    response = await client.chat.completions.create(
                        model=self.model,
                        messages=[
                            {"role": "system", "content": "Respond with valid JSON only."},
                            {"role": "user", "content": prompt},
                        ],
                        temperature=0.2,
                        max_tokens=1000,
                    )
                    content = (response.choices[0].message.content or "").strip()
                    parsed = self._parse_response(content)
                    if parsed:
                        return parsed
                    raise ValueError("Failed to parse JSON from model response")
                except Exception as exc:
                    logger.warning(
                        "LLM analysis attempt %s/3 failed for %s: %s",
                        attempt + 1,
                        symbol,
                        exc,
                    )
                    if attempt < 2:
                        await asyncio.sleep(2**attempt)
        finally:
            await self._close_client(client)

        return None

    async def analyze_and_store(
        self,
        db: Session,
        symbol: Symbol,
        timeframe: str = "1h",
        candles_limit: int = 200,
    ) -> Optional[Signal]:
        candles = self._load_recent_candles(db, symbol.symbol_id, candles_limit)
        if len(candles) < 50:
            logger.info("Skipping analysis for %s: only %s candles available", symbol.symbol, len(candles))
            return None
        if not self._candles_are_fresh(candles, timeframe):
            logger.warning("Skipping analysis for %s: candle data is stale", symbol.symbol)
            return None

        indicators = compute(candles)
        latest = candles[-1]
        current_price = float(latest["close"])
        duplicate = self._find_recent_duplicate_signal(db, symbol, timeframe, latest["timestamp"])
        if duplicate:
            logger.info("Skipping analysis for %s: signal already exists for latest candle window", symbol.symbol)
            return duplicate
        reference_index = -25 if len(candles) >= 25 else 0
        reference_price = float(candles[reference_index]["close"])
        change_24h = ((current_price - reference_price) / reference_price * 100) if reference_price else 0.0
        volume_ratio = indicators.get("volume_ratio") or 1.0
        volume_analysis = (
            f"Latest volume ratio vs 20-period average: {volume_ratio:.2f}x. "
            f"Current candle volume: {latest['volume']:.2f}."
        )
        result = await self.analyze(
            symbol=symbol.symbol,
            exchange=symbol.exchange,
            timeframe=timeframe,
            price=current_price,
            change_24h=change_24h,
            indicators=indicators,
            price_action=indicators.get("price_action_summary", ""),
            volume_analysis=volume_analysis,
        )
        if not result:
            return None

        signal = Signal(
            symbol_id=symbol.symbol_id,
            symbol=symbol.symbol,
            exchange=symbol.exchange,
            direction=self._normalize_direction(result.get("direction")),
            entry_price=self._as_float(result.get("entry_price")) or current_price,
            entry_min=self._as_float(result.get("entry_min")),
            entry_max=self._as_float(result.get("entry_max")),
            stop_loss=self._as_float(result.get("stop_loss")),
            take_profit=self._as_float(result.get("take_profit")),
            take_profit_2=self._as_float(result.get("take_profit_2")),
            confidence=self._as_int(result.get("confidence"), default=50),
            setup_type=str(result.get("setup_type") or "unspecified").strip().lower(),
            time_horizon=str(result.get("time_horizon") or "swing").strip().lower(),
            risk_reward=self._as_float(result.get("risk_reward")),
            invalidation=str(result.get("invalidation") or "").strip(),
            reasoning=str(result.get("reasoning") or "").strip(),
            indicators_data=json.dumps(indicators),
            llm_model=self.model,
            analysis_type="ai",
            raw_response=json.dumps(result),
            timestamp=utc_now(),
        )
        db.add(signal)
        db.commit()
        db.refresh(signal)

        self._auto_execute_paper_trade(db, symbol, signal)
        return signal

    def _auto_execute_paper_trade(self, db: Session, symbol: Symbol, signal: Signal) -> None:
        if not settings.auto_trade_enabled:
            return
        if signal.direction not in {"buy", "sell"}:
            return
        if signal.confidence < settings.auto_trade_min_confidence:
            logger.info(
                "Skipping auto-trade for %s: confidence %s below threshold %s",
                symbol.symbol,
                signal.confidence,
                settings.auto_trade_min_confidence,
            )
            return

        open_trade = db.exec(
            select(PaperTrade).where(
                PaperTrade.symbol_id == symbol.symbol_id,
                PaperTrade.status == "open",
            )
        ).first()
        if open_trade:
            return
        open_trade_count = len(
            db.exec(select(PaperTrade).where(PaperTrade.status == "open")).all()
        )
        if open_trade_count >= settings.max_open_trades:
            logger.info(
                "Skipping auto-trade for %s: open trade limit %s reached",
                symbol.symbol,
                settings.max_open_trades,
            )
            return

        direction = "long" if signal.direction == "buy" else "short"
        entry_price = signal.entry_price or 0.0
        if entry_price <= 0:
            return
        stop_loss, take_profit, take_profit_2 = self._normalize_trade_levels(
            direction=direction,
            entry_price=entry_price,
            stop_loss=signal.stop_loss,
            take_profit=signal.take_profit,
            take_profit_2=signal.take_profit_2,
        )
        if stop_loss is None or take_profit is None:
            return
        risk_reward = self._risk_reward_ratio(direction, entry_price, stop_loss, take_profit)
        if risk_reward < settings.min_risk_reward_ratio:
            logger.info(
                "Skipping auto-trade for %s: risk/reward %.2f below threshold %.2f",
                symbol.symbol,
                risk_reward,
                settings.min_risk_reward_ratio,
            )
            return

        quantity = max((settings.initial_capital * (settings.max_position_pct / 100.0)) / entry_price, 0.0)
        if quantity <= 0:
            return
        trade = PaperTrade(
            symbol_id=symbol.symbol_id,
            direction=direction,
            entry_price=entry_price,
            quantity=round(quantity, 8),
            current_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            take_profit_2=take_profit_2,
            strategy_id=None,
            source_signal_id=signal.id,
            notes=f"Auto-executed from signal #{signal.id}",
        )
        db.add(trade)
        db.commit()
        db.refresh(trade)
        signal.paper_trade_id = trade.id
        db.add(signal)
        db.commit()

    def _load_recent_candles(self, db: Session, symbol_id: int, limit: int) -> list[dict[str, Any]]:
        stmt = (
            select(Candle)
            .where(Candle.symbol_id == symbol_id)
            .order_by(Candle.timestamp.desc())
            .limit(limit)
        )
        records = list(db.exec(stmt).all())
        records.reverse()
        return [
            {
                "timestamp": candle.timestamp,
                "open": candle.open,
                "high": candle.high,
                "low": candle.low,
                "close": candle.close,
                "volume": candle.volume,
            }
            for candle in records
        ]

    def _parse_response(self, content: str) -> Optional[dict[str, Any]]:
        cleaned = content.strip()
        if cleaned.startswith("```"):
            lines = cleaned.splitlines()
            cleaned = "\n".join(lines[1:-1]).strip()

        parsed = None
        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError:
            start = cleaned.find("{")
            end = cleaned.rfind("}")
            if start == -1 or end == -1 or end <= start:
                return None
            try:
                parsed = json.loads(cleaned[start : end + 1])
            except json.JSONDecodeError:
                return None
        if not isinstance(parsed, dict):
            return None
        return self._normalize_signal_payload(parsed)

    def _normalize_signal_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "direction": self._normalize_direction(payload.get("direction")),
            "confidence": self._as_int(payload.get("confidence"), default=50),
            "setup_type": self._normalize_label(payload.get("setup_type"), default="unspecified"),
            "time_horizon": self._normalize_label(payload.get("time_horizon"), default="swing"),
            "entry_min": self._as_float(payload.get("entry_min")),
            "entry_max": self._as_float(payload.get("entry_max")),
            "entry_price": self._as_float(payload.get("entry_price")),
            "stop_loss": self._as_float(payload.get("stop_loss")),
            "take_profit": self._as_float(payload.get("take_profit")),
            "take_profit_2": self._as_float(payload.get("take_profit_2")),
            "risk_reward": self._as_float(payload.get("risk_reward")),
            "invalidation": str(payload.get("invalidation") or "").strip(),
            "reasoning": str(payload.get("reasoning") or "").strip(),
        }

    def _normalize_label(self, value: Any, default: str) -> str:
        normalized = str(value or default).strip().lower().replace(" ", "_").replace("-", "_")
        return normalized or default

    def _normalize_direction(self, direction: Any) -> str:
        normalized = str(direction or "hold").strip().lower()
        if normalized not in {"buy", "sell", "hold"}:
            return "hold"
        return normalized

    def _as_float(self, value: Any) -> Optional[float]:
        if value in (None, "", "null"):
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _as_int(self, value: Any, default: int = 0) -> int:
        try:
            return max(0, min(100, int(value)))
        except (TypeError, ValueError):
            return default

    def _candles_are_fresh(self, candles: list[dict[str, Any]], timeframe: str) -> bool:
        latest_timestamp = candles[-1]["timestamp"]
        if not isinstance(latest_timestamp, datetime):
            return False
        latest_timestamp = latest_timestamp.replace(tzinfo=None)
        age_seconds = (utc_now() - latest_timestamp).total_seconds()
        allowed_age = {
            "5m": 60 * 30,
            "15m": 60 * 60,
            "1h": 60 * 60 * 6,
            "4h": 60 * 60 * 18,
            "1d": 60 * 60 * 48,
        }.get(timeframe, 60 * 60 * 6)
        return age_seconds <= allowed_age

    def _find_recent_duplicate_signal(
        self,
        db: Session,
        symbol: Symbol,
        timeframe: str,
        latest_candle_timestamp: datetime,
    ) -> Optional[Signal]:
        duplicate_window_seconds = {
            "5m": 60 * 5,
            "15m": 60 * 15,
            "1h": 60 * 60,
            "4h": 60 * 60 * 4,
            "1d": 60 * 60 * 24,
        }.get(timeframe, 60 * 60)
        latest_signal = db.exec(
            select(Signal)
            .where(Signal.symbol_id == symbol.symbol_id)
            .order_by(Signal.timestamp.desc())
            .limit(1)
        ).first()
        if not latest_signal or not latest_signal.timestamp:
            return None
        delta = abs((latest_signal.timestamp - latest_candle_timestamp.replace(tzinfo=None)).total_seconds())
        return latest_signal if delta <= duplicate_window_seconds else None

    def _normalize_trade_levels(
        self,
        direction: str,
        entry_price: float,
        stop_loss: Optional[float],
        take_profit: Optional[float],
        take_profit_2: Optional[float],
    ) -> tuple[Optional[float], Optional[float], Optional[float]]:
        stop_loss = self._as_float(stop_loss)
        take_profit = self._as_float(take_profit)
        take_profit_2 = self._as_float(take_profit_2)

        if direction == "long":
            if stop_loss is None or stop_loss >= entry_price:
                stop_loss = round(entry_price * 0.98, 8)
            if take_profit is None or take_profit <= entry_price:
                take_profit = round(entry_price * 1.04, 8)
            if take_profit_2 is not None and take_profit_2 <= take_profit:
                take_profit_2 = None
        else:
            if stop_loss is None or stop_loss <= entry_price:
                stop_loss = round(entry_price * 1.02, 8)
            if take_profit is None or take_profit >= entry_price:
                take_profit = round(entry_price * 0.96, 8)
            if take_profit_2 is not None and take_profit_2 >= take_profit:
                take_profit_2 = None

        return stop_loss, take_profit, take_profit_2

    def _risk_reward_ratio(
        self,
        direction: str,
        entry_price: float,
        stop_loss: float,
        take_profit: float,
    ) -> float:
        if direction == "long":
            risk = max(entry_price - stop_loss, 0.0)
            reward = max(take_profit - entry_price, 0.0)
        else:
            risk = max(stop_loss - entry_price, 0.0)
            reward = max(entry_price - take_profit, 0.0)
        if risk <= 0:
            return 0.0
        return reward / risk
