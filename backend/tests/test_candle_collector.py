import asyncio
from datetime import datetime, timezone

from app.services.candle_collector import CandleCollector


class DummyResponse:
    def raise_for_status(self):
        return None

    def json(self):
        return [
            {
                "t": 1710000000000,
                "T": 1710003599999,
                "o": "100.0",
                "h": "110.0",
                "l": "90.0",
                "c": "105.0",
                "v": "1234.5",
            }
        ]


class DummyAsyncClient:
    posted_urls = []
    posted_payloads = []

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None

    async def post(self, url, json, headers=None):
        self.posted_urls.append(url)
        self.posted_payloads.append(json)
        return DummyResponse()


def test_candle_collector_uses_hyperliquid_info_candle_snapshot(monkeypatch):
    import app.services.candle_collector as candle_collector

    DummyAsyncClient.posted_urls = []
    DummyAsyncClient.posted_payloads = []
    monkeypatch.setattr(candle_collector.httpx, "AsyncClient", DummyAsyncClient)

    candles = asyncio.run(CandleCollector().fetch_hyperliquid_candles("PEPE", "1h", 1))

    assert DummyAsyncClient.posted_urls == ["https://api.hyperliquid.xyz/info"]
    payload = DummyAsyncClient.posted_payloads[0]
    assert payload["type"] == "candleSnapshot"
    assert payload["req"]["coin"] == "kPEPE"
    assert payload["req"]["interval"] == "1h"
    assert "startTime" in payload["req"]
    assert "endTime" in payload["req"]
    assert candles == [
        {
            "timestamp": datetime.fromtimestamp(1710000000000 / 1000, tz=timezone.utc),
            "open": 100.0,
            "high": 110.0,
            "low": 90.0,
            "close": 105.0,
            "volume": 1234.5,
        }
    ]
