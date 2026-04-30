from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session, create_engine

from app.database import get_db
from app.main import app as fastapi_app
from app.models.candle import Candle
from app.models.signal import Signal
from app.models.symbol import Symbol
import app.models  # noqa: F401 - ensure SQLModel metadata includes every table


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
    # Reuse the dependency override session factory by asking FastAPI for a route-bound session indirectly
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


def test_signals_route_serializes_persisted_signal_datetimes(client, db_session):
    symbol = add_symbol(db_session)
    signal = Signal(
        symbol_id=symbol.symbol_id,
        symbol=symbol.symbol,
        exchange=symbol.exchange,
        direction="hold",
        confidence=65,
        reasoning="Runtime smoke test signal",
        analysis_type="ai",
        timestamp=datetime(2026, 4, 30, 6, 22, 56, tzinfo=UTC),
    )
    db_session.add(signal)
    db_session.commit()

    response = client.get("/api/signals?limit=5")

    assert response.status_code == 200
    payload = response.json()
    assert payload[0]["symbol"] == "BTC"
    assert payload[0]["timestamp"].startswith("2026-04-30T06:22:56")


def test_frontend_core_api_contract_routes_return_json(client):
    paths = [
        "/api/health",
        "/api/health/status",
        "/api/watchlist",
        "/api/signals",
        "/api/portfolio/summary",
        "/api/portfolio/performance",
        "/api/portfolio",
        "/api/risk/profile",
        "/api/config",
        "/api/strategies",
        "/api/strategies/templates",
        "/api/backtest",
    ]
    for path in paths:
        response = client.get(path)
        assert response.status_code == 200, path
        assert "application/json" in response.headers["content-type"], path


def test_watchlist_create_duplicate_and_soft_delete_contract(client):
    create_payload = {
        "exchange": "hyperliquid",
        "symbol_type": "perp",
        "symbol": "BTC",
        "display_name": "BTC-PERP",
    }

    created = client.post("/api/watchlist", json=create_payload)
    assert created.status_code == 201
    created_payload = created.json()
    assert created_payload["symbol"] == "BTC"
    assert created_payload["exchange"] == "hyperliquid"
    assert created_payload["is_active"] is True
    assert isinstance(created_payload["symbol_id"], int)

    duplicate = client.post("/api/watchlist", json=create_payload)
    assert duplicate.status_code == 409

    listed = client.get("/api/watchlist")
    assert listed.status_code == 200
    assert [item["symbol"] for item in listed.json()] == ["BTC"]

    deleted = client.delete(f"/api/watchlist/{created_payload['symbol_id']}")
    assert deleted.status_code == 200
    assert deleted.json() == {"message": "Symbol removed"}

    listed_after_delete = client.get("/api/watchlist")
    assert listed_after_delete.status_code == 200
    assert listed_after_delete.json() == []


def test_candles_fetch_all_route_is_not_shadowed_by_symbol_id_route(client, monkeypatch):
    from app.api import candles

    async def fake_collect_all_hyperliquid(self, db=None):
        return {"BTC": 0}

    def fake_collect_all_yahoo(self, db=None):
        return {"SPY": 0}

    monkeypatch.setattr(candles.CandleCollector, "collect_all_hyperliquid", fake_collect_all_hyperliquid)
    monkeypatch.setattr(candles.CandleCollector, "collect_all_yahoo", fake_collect_all_yahoo)

    response = client.post("/api/candles/fetch/all")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_candles_stored"] == 0
    assert payload["hyperliquid"] == {"BTC": 0}
    assert payload["yahoo"] == {"SPY": 0}


def test_candles_list_contract_returns_chronological_candles(client, db_session):
    symbol = add_symbol(db_session)
    now = datetime.now(UTC).replace(tzinfo=None)
    newer = Candle(symbol_id=symbol.symbol_id, timestamp=now, open=11, high=13, low=10, close=12, volume=100)
    older = Candle(symbol_id=symbol.symbol_id, timestamp=now - timedelta(hours=1), open=10, high=12, low=9, close=11, volume=90)
    db_session.add(older)
    db_session.add(newer)
    db_session.commit()

    response = client.get(f"/api/candles/{symbol.symbol_id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["symbol"] == "BTC-PERP"
    assert payload["timeframe"] == "1h"
    assert [candle["close"] for candle in payload["candles"]] == [11.0, 12.0]


def test_signals_analyze_runs_synchronous_analysis_contract(client, db_session, monkeypatch):
    from app.services.llm_analysis import LLMAnalysisService

    symbol = add_symbol(db_session)
    calls = []

    async def fake_analyze_and_store(self, db, sym, timeframe="1h", candles_limit=200):
        calls.append((sym.symbol_id, sym.symbol, sym.exchange, timeframe, candles_limit))
        signal = Signal(
            symbol_id=sym.symbol_id,
            symbol=sym.symbol,
            exchange=sym.exchange,
            direction="buy",
            confidence=82,
            setup_type="breakout",
            reasoning="Test analysis",
            analysis_type="ai",
            timestamp=datetime(2026, 4, 30, 7, 0, 0, tzinfo=UTC),
        )
        db.add(signal)
        db.flush()
        return signal

    monkeypatch.setattr(LLMAnalysisService, "analyze_and_store", fake_analyze_and_store)

    response = client.post(f"/api/signals/analyze/{symbol.symbol}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["symbol"] == "BTC"
    assert payload["direction"] == "buy"
    assert payload["confidence"] == 82
    assert payload["setup_type"] == "breakout"
    assert isinstance(payload["signal_id"], int)
    assert calls == [(symbol.symbol_id, "BTC", "hyperliquid", "1h", 200)]


def test_portfolio_create_and_summary_contract(client, db_session, monkeypatch):
    from app.api import portfolio

    symbol = add_symbol(db_session, symbol="AAPL", exchange="yahoo")
    monkeypatch.setattr(portfolio, "get_current_price", lambda symbol_name: 110.0)

    created = client.post(
        "/api/portfolio",
        json={
            "symbol_id": symbol.symbol_id,
            "direction": "long",
            "entry_price": 100.0,
            "quantity": 2.0,
            "stop_loss": 95.0,
            "take_profit": 120.0,
            "notes": "manual test trade",
        },
    )

    assert created.status_code == 201
    trade = created.json()
    assert trade["symbol"] == "AAPL"
    assert trade["direction"] == "long"
    assert trade["current_price"] == 100.0
    assert trade["status"] == "open"

    listed = client.get("/api/portfolio")
    assert listed.status_code == 200
    listed_trade = listed.json()[0]
    assert listed_trade["current_price"] == 110.0
    assert listed_trade["pnl"] == 20.0
    assert listed_trade["pnl_pct"] == 10.0

    summary = client.get("/api/portfolio/summary")
    assert summary.status_code == 200
    assert summary.json()["open_positions"] == 1
    assert summary.json()["unrealized_pnl"] == 20.0


def test_strategy_create_list_and_delete_contract(client):
    payload = {
        "name": "RSI dip buyer",
        "description": "Buy when RSI is oversold",
        "exchange": "hyperliquid",
        "timeframe": "1h",
        "conditions": [{"indicator": "rsi", "operator": "lt", "value": 30}],
    }

    created = client.post("/api/strategies", json=payload)
    assert created.status_code == 201
    strategy = created.json()
    assert strategy["name"] == "RSI dip buyer"
    assert strategy["conditions"] == payload["conditions"]
    assert strategy["is_active"] is True

    listed = client.get("/api/strategies")
    assert listed.status_code == 200
    assert [item["name"] for item in listed.json()] == ["RSI dip buyer"]

    deleted = client.delete(f"/api/strategies/{strategy['id']}")
    assert deleted.status_code == 200
    assert deleted.json() == {"message": "Strategy deactivated"}

    listed_after_delete = client.get("/api/strategies")
    assert listed_after_delete.status_code == 200
    assert listed_after_delete.json() == []


def test_risk_position_size_calculates_fixed_fractional_and_kelly(client):
    fixed = client.post(
        "/api/risk/position-size",
        json={
            "symbol": "BTC",
            "direction": "long",
            "entry_price": 100.0,
            "stop_loss": 95.0,
            "account_equity": 10000.0,
            "method": "fixed_fractional",
            "risk_pct": 1.0,
            "max_position_pct": 25.0,
        },
    )
    assert fixed.status_code == 200
    fixed_payload = fixed.json()
    assert fixed_payload["risk_amount"] == 100.0
    assert fixed_payload["quantity"] == 20.0
    assert fixed_payload["notional"] == 2000.0
    assert fixed_payload["warnings"] == []

    kelly = client.post(
        "/api/risk/position-size",
        json={
            "symbol": "BTC",
            "direction": "long",
            "entry_price": 100.0,
            "stop_loss": 95.0,
            "account_equity": 10000.0,
            "method": "kelly",
            "win_rate": 0.55,
            "reward_risk": 2.0,
        },
    )
    assert kelly.status_code == 200
    assert 0 < kelly.json()["recommended_risk_pct"] <= 5.0


def test_strategy_templates_can_be_listed_and_created(client):
    listed = client.get("/api/strategies/templates")
    assert listed.status_code == 200
    templates = listed.json()
    template_ids = {item["id"] for item in templates}
    assert {"rsi_reversal", "macd_trend", "bollinger_squeeze"}.issubset(template_ids)
    rsi_template = next(item for item in templates if item["id"] == "rsi_reversal")
    assert rsi_template["conditions"]
    assert rsi_template["risk_profile"]["default_risk_pct"] <= 1.0

    created = client.post("/api/strategies/templates/rsi_reversal/create")
    assert created.status_code == 201
    strategy = created.json()
    assert strategy["name"] == rsi_template["name"]
    assert strategy["conditions"] == rsi_template["conditions"]


def test_portfolio_performance_returns_equity_drawdown_and_monthly_pnl(client, db_session):
    symbol = add_symbol(db_session, symbol="AAPL", exchange="yahoo")
    from app.models.paper_trade import PaperTrade

    db_session.add(
        PaperTrade(
            symbol_id=symbol.symbol_id,
            direction="long",
            entry_price=100,
            quantity=1,
            exit_price=110,
            status="closed",
            pnl=10,
            pnl_pct=10,
            entry_time=datetime(2026, 1, 5, tzinfo=UTC),
            exit_time=datetime(2026, 1, 6, tzinfo=UTC),
            close_reason="take_profit",
        )
    )
    db_session.add(
        PaperTrade(
            symbol_id=symbol.symbol_id,
            direction="long",
            entry_price=100,
            quantity=1,
            exit_price=95,
            status="closed",
            pnl=-5,
            pnl_pct=-5,
            entry_time=datetime(2026, 2, 5, tzinfo=UTC),
            exit_time=datetime(2026, 2, 6, tzinfo=UTC),
            close_reason="stop_loss",
        )
    )
    db_session.commit()

    response = client.get("/api/portfolio/performance")
    assert response.status_code == 200
    payload = response.json()
    assert payload["total_return"] == 5.0
    assert payload["win_rate"] == 50.0
    assert payload["monthly_pnl"]["2026-01"] == 10.0
    assert payload["monthly_pnl"]["2026-02"] == -5.0
    assert payload["equity_curve"][-1]["equity"] == 10005.0
    assert payload["max_drawdown"] > 0


def test_backtest_optimizer_returns_ranked_parameter_runs(client):
    payload = {
        "base_conditions": [{"indicator": "rsi", "operator": "lt", "value": 30}],
        "parameter_grid": {"rsi": [25, 30, 35]},
        "mock_metrics": True,
    }
    response = client.post("/api/backtest/optimize", json=payload)
    assert response.status_code == 200
    results = response.json()["results"]
    assert len(results) == 3
    assert results[0]["rank"] == 1
    assert results[0]["score"] >= results[-1]["score"]
