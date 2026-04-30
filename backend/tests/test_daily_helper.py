from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session, create_engine

import app.models  # noqa: F401 - ensure SQLModel metadata includes every table
from app.database import get_db
from app.main import app as fastapi_app
from app.models.candle import Candle
from app.models.paper_trade import PaperTrade
from app.models.signal import Signal
from app.models.symbol import Symbol
from app.services.llm_analysis import LLMAnalysisService


@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)

    def override_get_db():
        with Session(engine) as session:
            yield session

    fastapi_app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(fastapi_app) as test_client:
            yield test_client
    finally:
        fastapi_app.dependency_overrides.clear()


@pytest.fixture()
def db_session(client):
    override = fastapi_app.dependency_overrides[get_db]
    session_generator = override()
    session = next(session_generator)
    try:
        yield session
    finally:
        session.close()
        try:
            next(session_generator)
        except StopIteration:
            pass


def add_symbol(session: Session, symbol: str = "BTC", exchange: str = "hyperliquid") -> Symbol:
    item = Symbol(
        exchange=exchange,
        symbol_type="perp" if exchange == "hyperliquid" else "stock",
        symbol=symbol,
        display_name=f"{symbol}-PERP" if exchange == "hyperliquid" else symbol,
        is_active=True,
    )
    session.add(item)
    session.commit()
    session.refresh(item)
    return item


def test_daily_brief_generate_stores_structured_morning_summary(client, db_session, monkeypatch):
    symbol = add_symbol(db_session)
    now = datetime.now(UTC).replace(tzinfo=None)
    db_session.add(
        Signal(
            symbol_id=symbol.symbol_id,
            symbol="BTC",
            exchange="hyperliquid",
            direction="buy",
            confidence=82,
            setup_type="breakout",
            time_horizon="intraday",
            entry_price=100.0,
            entry_min=99.5,
            entry_max=101.0,
            stop_loss=96.0,
            take_profit=108.0,
            take_profit_2=112.0,
            risk_reward=2.0,
            invalidation="Failure below 96",
            reasoning="Momentum breakout with strong volume.",
            timestamp=now,
        )
    )
    db_session.add(Candle(symbol_id=symbol.symbol_id, timestamp=now, open=99, high=102, low=98, close=101, volume=1000))
    db_session.add(PaperTrade(symbol_id=symbol.symbol_id, direction="long", entry_price=100, quantity=1, current_price=101, status="open"))
    db_session.commit()

    response = client.post("/api/daily-brief/generate")

    assert response.status_code == 201
    payload = response.json()
    assert payload["market_regime"] in {"bullish", "bearish", "choppy", "risk-off", "risk-on", "mixed"}
    assert "BTC" in payload["summary"]
    assert payload["top_opportunities"][0]["symbol"] == "BTC"
    assert payload["top_opportunities"][0]["direction"] == "buy"
    assert payload["open_positions_summary"]["open_positions"] == 1

    latest = client.get("/api/daily-brief/latest")
    assert latest.status_code == 200
    assert latest.json()["id"] == payload["id"]


def test_health_status_reports_named_components_and_freshness(client, db_session, monkeypatch):
    symbol = add_symbol(db_session)
    now = datetime.now(UTC).replace(tzinfo=None)
    db_session.add(Candle(symbol_id=symbol.symbol_id, timestamp=now - timedelta(minutes=5), open=1, high=2, low=1, close=2, volume=10))
    db_session.add(Signal(symbol_id=symbol.symbol_id, symbol="BTC", exchange="hyperliquid", direction="hold", timestamp=now - timedelta(minutes=2)))
    db_session.commit()

    class FakeRedis:
        def ping(self):
            return True

    monkeypatch.setattr("app.api.health.redis.from_url", lambda url: FakeRedis())

    class FakeResponse:
        status_code = 200

    class FakeAsyncClient:
        def __init__(self, timeout):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def get(self, *args, **kwargs):
            return FakeResponse()

    monkeypatch.setattr("app.api.health.httpx.AsyncClient", FakeAsyncClient)

    response = client.get("/api/health/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["components"]["database"]["status"] == "ok"
    assert payload["components"]["redis"]["status"] == "ok"
    assert payload["components"]["llm"]["status"] == "ok"
    assert payload["data"]["latest_candle_at"] is not None
    assert payload["data"]["fresh"] is True
    assert payload["signals"]["latest_signal_at"] is not None


def test_llm_parser_normalizes_structured_signal_fields():
    service = LLMAnalysisService(base_url="http://example.test/v1", api_key="test", model="test-model")
    parsed = service._parse_response(
        """
        ```json
        {
          "direction": "BUY",
          "confidence": "88",
          "setup_type": "Breakout",
          "time_horizon": "Intraday",
          "entry_min": "100.5",
          "entry_max": "101.5",
          "entry_price": "101",
          "stop_loss": "98",
          "take_profit": "107",
          "take_profit_2": "112",
          "risk_reward": "2.0",
          "invalidation": "Breaks below 98",
          "reasoning": "Price reclaimed resistance."
        }
        ```
        """
    )

    assert parsed == {
        "direction": "buy",
        "confidence": 88,
        "setup_type": "breakout",
        "time_horizon": "intraday",
        "entry_min": 100.5,
        "entry_max": 101.5,
        "entry_price": 101.0,
        "stop_loss": 98.0,
        "take_profit": 107.0,
        "take_profit_2": 112.0,
        "risk_reward": 2.0,
        "invalidation": "Breaks below 98",
        "reasoning": "Price reclaimed resistance.",
    }
