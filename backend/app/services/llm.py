"""LLM integration service — hybrid analysis pipeline."""

import json
import logging
from typing import Optional

import httpx
from app.config import settings

logger = logging.getLogger(__name__)

LLM_ANALYSIS_PROMPT = """You are an expert quantitative trader. Analyze the following market data for {symbol} on {exchange} ({timeframe}).

Technical Indicators:
{indicators}

Recent Price Action:
{price_action}

Additional Context:
{context}

Return ONLY valid JSON with this structure:
{{
  "direction": "buy | sell | hold",
  "entry_price": float,
  "stop_loss": float,
  "take_profit": float,
  "take_profit_2": float | null,
  "confidence": int (0-100),
  "reasoning": "detailed explanation"
}}

Do not include markdown, backticks, or any other formatting — only raw JSON."""


async def analyze_symbol(
    symbol: str,
    indicators: dict,
    price_action: str,
    context: str,
    exchange: str = "hyperliquid",
    timeframe: str = "1h",
) -> Optional[dict]:
    """Run hybrid analysis: compute indicators in Python, send to LLM for reasoning."""
    indicators_str = json.dumps(indicators, indent=2)

    prompt = LLM_ANALYSIS_PROMPT.format(
        symbol=symbol,
        exchange=exchange,
        timeframe=timeframe,
        indicators=indicators_str,
        price_action=price_action,
        context=context,
    )

    body = {
        "model": settings.llm_model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
        "max_tokens": 1024,
        "stream": False,
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        for attempt in range(3):
            try:
                resp = await client.post(
                    f"{settings.llm_base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {settings.llm_api_key}"},
                    json=body,
                )
                resp.raise_for_status()
                data = resp.json()
                content = data["choices"][0]["message"]["content"].strip()

                # Strip markdown if present
                if content.startswith("```"):
                    lines = content.split("\n")
                    content = "\n".join(lines[1:-1])

                result = json.loads(content)
                logger.info(f"LLM analysis for {symbol}: {result.get('direction')} (confidence {result.get('confidence', 0)})")
                return result

            except Exception as e:
                logger.warning(f"LLM call failed (attempt {attempt + 1}/3) for {symbol}: {e}")
                if attempt < 2:
                    await httpx.AsyncClient().aclose()
                    await httpx.AsyncClient().aclose()  # force cleanup
                    import asyncio
                    await asyncio.sleep(2 ** attempt)
                else:
                    logger.error(f"LLM analysis failed for {symbol} after 3 attempts")
                    return None

    return None
