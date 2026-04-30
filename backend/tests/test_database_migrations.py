from pathlib import Path

from sqlalchemy import inspect, text
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, create_engine

from app import database, seed


def test_sqlite_migrations_add_symbol_columns_to_legacy_symbols_table(monkeypatch, tmp_path):
    db_path = tmp_path / "legacy.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE symbols (symbol_id INTEGER PRIMARY KEY, exchange VARCHAR, display_name VARCHAR)"))
        conn.execute(text("INSERT INTO symbols (symbol_id, exchange, display_name) VALUES (1, 'hyperliquid', 'BTC-PERP')"))

    monkeypatch.setattr(database, "engine", engine)
    monkeypatch.setattr(database.settings, "database_url", f"sqlite:///{db_path}")

    database._run_lightweight_migrations()

    columns = {column["name"] for column in inspect(engine).get_columns("symbols")}
    assert "symbol" in columns
    assert "symbol_type" in columns
    assert "is_active" in columns
    assert "added_at" in columns

    with engine.connect() as conn:
        row = conn.execute(text("SELECT symbol, symbol_type, is_active FROM symbols WHERE symbol_id = 1")).mappings().one()

    assert row["symbol"] == "BTC"
    assert row["symbol_type"] == "perp"
    assert row["is_active"] == 1


def test_seed_assigns_ids_when_legacy_symbols_table_does_not_autoincrement(monkeypatch, tmp_path):
    db_path = tmp_path / "legacy-no-autoincrement.db"
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE symbols (symbol_id INTEGER NOT NULL, exchange VARCHAR, display_name VARCHAR)"))
        conn.execute(text("INSERT INTO symbols (symbol_id, exchange, display_name) VALUES (1, 'hyperliquid', 'BTC-PERP')"))

    monkeypatch.setattr(database, "engine", engine)
    monkeypatch.setattr(database.settings, "database_url", f"sqlite:///{db_path}")
    monkeypatch.setattr(seed, "HYPERLIQUID_PERPS", [
        {"symbol": "BTC", "display_name": "BTC-PERP"},
        {"symbol": "ETH", "display_name": "ETH-PERP"},
    ])
    database._run_lightweight_migrations()

    with Session(engine) as session:
        seed._seed_hyperliquid(session)
        session.commit()

    with engine.connect() as conn:
        rows = conn.execute(text("SELECT symbol_id, symbol FROM symbols ORDER BY symbol_id")).all()

    assert rows == [(1, "BTC"), (2, "ETH")]
