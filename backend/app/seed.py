"""Seed the database with default watchlist symbols."""

from sqlalchemy import inspect, text
from sqlmodel import Session, select

from app.database import engine, init_db
from app.models.symbol import Symbol
from app.services.hyperliquid import HYPERLIQUID_PERPS
from app.services.yahoo_finance import YAHOO_POPULAR


def seed() -> None:
    init_db()

    with Session(engine) as session:
        _seed_hyperliquid(session)
        _seed_yahoo(session)
        session.commit()


def _seed_hyperliquid(session: Session) -> None:
    needs_manual_id = _needs_manual_symbol_id(session)
    next_id = _next_symbol_id(session) if needs_manual_id else None

    for perp in HYPERLIQUID_PERPS:
        existing = session.exec(
            select(Symbol).where(
                Symbol.symbol == perp["symbol"],
                Symbol.exchange == "hyperliquid",
            )
        ).first()
        if existing:
            continue

        kwargs = {"symbol_id": next_id} if needs_manual_id else {}
        session.add(
            Symbol(
                **kwargs,
                symbol=perp["symbol"],
                display_name=perp["display_name"],
                exchange="hyperliquid",
                symbol_type="perp",
                is_active=True,
            )
        )
        if needs_manual_id:
            next_id += 1


def _seed_yahoo(session: Session) -> None:
    needs_manual_id = _needs_manual_symbol_id(session)
    next_id = _next_symbol_id(session) if needs_manual_id else None

    for asset in YAHOO_POPULAR:
        existing = session.exec(
            select(Symbol).where(
                Symbol.symbol == asset["symbol"],
                Symbol.exchange == "yahoo",
            )
        ).first()
        if existing:
            continue

        kwargs = {"symbol_id": next_id} if needs_manual_id else {}
        session.add(
            Symbol(
                **kwargs,
                symbol=asset["symbol"],
                display_name=asset["display_name"],
                exchange="yahoo",
                symbol_type=asset["type"],
                is_active=True,
            )
        )
        if needs_manual_id:
            next_id += 1


def _needs_manual_symbol_id(session: Session) -> bool:
    """Return True for legacy SQLite schemas where symbol_id is NOT NULL but not a primary key."""
    bind = session.get_bind()
    columns = inspect(bind).get_columns("symbols")
    symbol_id = next((column for column in columns if column["name"] == "symbol_id"), None)
    return bool(symbol_id and not symbol_id.get("primary_key"))


def _next_symbol_id(session: Session) -> int:
    result = session.exec(text("SELECT COALESCE(MAX(symbol_id), 0) + 1 FROM symbols")).one()
    try:
        return int(result[0])
    except (TypeError, KeyError):
        return int(result)


if __name__ == "__main__":
    seed()
    print("Database seeded successfully")
