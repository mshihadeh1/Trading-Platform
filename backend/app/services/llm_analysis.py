"""LLM analysis service - hybrid approach: Python computes indicators, LLM provides reasoning."""

import json
import logging
from datetime import datetime
from typing import Optional

from openai import AsyncOpenAI

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

{additional_context}

Rules:
- Provide clear entry, stop-loss, and take-profit levels
- Stop-loss should be 1-3% away from entry for short-term, 3-7% for longer-term
- Take-profit should offer at least 2:1 risk/reward ratio
- Be specific with your reasoning, referencing the indicators

Return ONLY valid JSON (no markdown, no explanation):
{{
  "direction": "buy | sell | hold",
  "entry_price": float,
  "stop_loss": float,
  "take_profit": float,
  "take_profit_2": float or null,
  "confidence": int (0-100),
  "reasoning": "detailed analysis explanation"
}}
"""


class LLMAnalysisService:
    def __init__(self, base_url: str, api_key: str, model: str):
        self.client = AsyncOpenAI(base_url=base_url, api_key=api_key)
        self.model = model

    async def analyze(self, symbol: str, exchange: str, timeframe: str,
                      price: float, change_24h: float, indicators: dict,
                      price_action: str, volume_analysis: str,
                      additional_context: str = "") -> Optional[dict]:
        """Run hybrid analysis: compute indicators + get LLM reasoning."""
        # Format indicators for the prompt
        indicators_str = "\n".join(f"- {k}: {v}" for k, v in indicators.items())

        prompt = ANALYSIS_PROMPT.format(
            symbol=symbol,
            exchange=exchange,
            timeframe=timeframe,
            price=price,
            change_24h=round(change_24h, 2),
            indicators=indicators_str,
            price_action=price_action,
            volume_analysis=volume_analysis,
            additional_context=additional_context,
        )

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a quantitative trading AI. Always respond with valid JSON."},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=1000,
            )

            content = response.choices[0].message.content.strip()
            # Strip any markdown code blocks
            content = content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()

            return json.loads(content)
        except Exception as e:
            logger.error(f"LLM analysis failed for {symbol}: {e}")
            return None

    async def analyze_strategy(self, symbol: str, timeframe: str,
                                indicator_values: dict, strategy_conditions: list) -> Optional[dict]:
        """Evaluate a strategy's conditions against current indicator values."""
        conditions_eval = []
        for cond in strategy_conditions:
            indicator = cond.get("indicator", "")
            operator = cond.get("operator", "")
            value = cond.get("value", 0)
            actual = indicator_values.get(indicator, 0)

            if operator == "lt":
                hit = actual < value
            elif operator == "gt":
                hit = actual > value
            elif operator == "lte":
                hit = actual <= value
            elif operator == "gte":
                hit = actual >= value
            elif operator == "crosses_above":
                hit = actual > value and indicator_values.get(f"{indicator}_prev", 0) <= value
            elif operator == "crosses_below":
                hit = actual < value and indicator_values.get(f"{indicator}_prev", 0) >= value
            else:
                hit = False

            conditions_eval.append({
                "condition": f"{indicator} {operator} {value}",
                "actual": actual,
                "hit": hit,
            })

        all_hit = all(c["hit"] for c in conditions_eval) if conditions_eval else False

        return {
            "all_conditions_met": all_hit,
            "conditions_evaluated": conditions_eval,
        }
