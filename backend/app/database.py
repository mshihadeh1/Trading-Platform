from pathlib import Path

from sqlmodel import SQLModel, Session, create_engine
from sqlalchemy import inspect, text
from app.config import settings
import app.models  # noqa: F401


engine = create_engine(settings.database_url, echo=False)


def init_db():
    if settings.database_url.startswith("sqlite:///"):
        db_path = settings.database_url.removeprefix("sqlite:///")
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    SQLModel.metadata.create_all(engine)
    _run_lightweight_migrations()


def get_db():
    with Session(engine) as session:
        yield session


def _run_lightweight_migrations():
    if not settings.database_url.startswith("sqlite:///"):
        return

    inspector = inspect(engine)
    migrations = {
        "symbols": {
            "symbol": "ALTER TABLE symbols ADD COLUMN symbol VARCHAR",
            "symbol_type": "ALTER TABLE symbols ADD COLUMN symbol_type VARCHAR DEFAULT 'perp'",
            "added_at": "ALTER TABLE symbols ADD COLUMN added_at DATETIME",
            "is_active": "ALTER TABLE symbols ADD COLUMN is_active BOOLEAN DEFAULT 1",
        },
        "signals": {
            "paper_trade_id": "ALTER TABLE signals ADD COLUMN paper_trade_id INTEGER",
            "entry_min": "ALTER TABLE signals ADD COLUMN entry_min FLOAT",
            "entry_max": "ALTER TABLE signals ADD COLUMN entry_max FLOAT",
            "setup_type": "ALTER TABLE signals ADD COLUMN setup_type VARCHAR DEFAULT 'unspecified'",
            "time_horizon": "ALTER TABLE signals ADD COLUMN time_horizon VARCHAR DEFAULT 'swing'",
            "risk_reward": "ALTER TABLE signals ADD COLUMN risk_reward FLOAT",
            "invalidation": "ALTER TABLE signals ADD COLUMN invalidation VARCHAR DEFAULT ''",
        },
        "paper_trades": {
            "current_price": "ALTER TABLE paper_trades ADD COLUMN current_price FLOAT",
            "source_signal_id": "ALTER TABLE paper_trades ADD COLUMN source_signal_id INTEGER",
            "close_reason": "ALTER TABLE paper_trades ADD COLUMN close_reason VARCHAR",
        },
        "backtest_results": {
            "symbol_id": "ALTER TABLE backtest_results ADD COLUMN symbol_id INTEGER",
            "timeframe": "ALTER TABLE backtest_results ADD COLUMN timeframe VARCHAR DEFAULT '1h'",
            "initial_capital": "ALTER TABLE backtest_results ADD COLUMN initial_capital FLOAT DEFAULT 10000.0",
            "fee_bps": "ALTER TABLE backtest_results ADD COLUMN fee_bps FLOAT DEFAULT 10.0",
            "slippage_bps": "ALTER TABLE backtest_results ADD COLUMN slippage_bps FLOAT DEFAULT 5.0",
        },
    }

    with engine.begin() as conn:
        for table_name, columns in migrations.items():
            if not inspector.has_table(table_name):
                continue
            existing = {column["name"] for column in inspector.get_columns(table_name)}
            for column_name, statement in columns.items():
                if column_name not in existing:
                    conn.execute(text(statement))

        if inspector.has_table("symbols"):
            symbol_columns = {column["name"] for column in inspect(engine).get_columns("symbols")}
            if {"symbol", "display_name"}.issubset(symbol_columns):
                conn.execute(
                    text(
                        """
                        UPDATE symbols
                        SET symbol = CASE
                            WHEN symbol IS NOT NULL AND symbol != '' THEN symbol
                            WHEN instr(display_name, '-PERP') > 0 THEN substr(display_name, 1, instr(display_name, '-PERP') - 1)
                            ELSE display_name
                        END
                        WHERE symbol IS NULL OR symbol = ''
                        """
                    )
                )
            if "added_at" in symbol_columns:
                conn.execute(
                    text("UPDATE symbols SET added_at = CURRENT_TIMESTAMP WHERE added_at IS NULL OR added_at = ''")
                )
