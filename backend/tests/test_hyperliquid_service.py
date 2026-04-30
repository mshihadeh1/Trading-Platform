import asyncio

from app.services import hyperliquid


class DummyResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class DummyAsyncClient:
    posted_urls = []
    posted_payloads = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return None

    async def post(self, url, json):
        self.posted_urls.append(url)
        self.posted_payloads.append(json)
        if json["type"] == "allMids":
            return DummyResponse({"BTC": "100000"})
        return DummyResponse([])


def test_hyperliquid_info_posts_to_info_endpoint(monkeypatch):
    DummyAsyncClient.posted_urls = []
    DummyAsyncClient.posted_payloads = []
    monkeypatch.setattr(hyperliquid.httpx, "AsyncClient", DummyAsyncClient)

    result = asyncio.run(hyperliquid.get_info("BTC"))

    assert result == {"BTC": "100000"}
    assert DummyAsyncClient.posted_urls == ["https://api.hyperliquid.xyz/info"]
    assert DummyAsyncClient.posted_payloads == [{"type": "allMids"}]


def test_hyperliquid_candles_post_to_info_endpoint(monkeypatch):
    DummyAsyncClient.posted_urls = []
    DummyAsyncClient.posted_payloads = []
    monkeypatch.setattr(hyperliquid.httpx, "AsyncClient", DummyAsyncClient)

    result = asyncio.run(hyperliquid.get_candles("BTC", "1h", 1))

    assert result == []
    assert DummyAsyncClient.posted_urls == ["https://api.hyperliquid.xyz/info"]
    assert DummyAsyncClient.posted_payloads[0]["type"] == "candle"
    assert DummyAsyncClient.posted_payloads[0]["coin"] == "BTC"
