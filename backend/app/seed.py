"""Seed the database with default watchlist symbols."""

from sqlmodel import Session, select, text

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


def _next_symbol_id(session: Session) -> int:
    """Return the next available symbol_id (max + 1, or 1 if empty)."""
    result = session.exec(text("SELECT COALESCE(MAX(symbol_id), 0) + 1 FROM symbols"))
    row = result.first()
    if row is None:
        return 1
    if isinstance(row, tuple):
        return int(row[0])
    if hasattr(row, "_mapping"):
        return int(row[0])
    return int(row)


def _seed_hyperliquid(session: Session) -> None:
    next_id = _next_symbol_id(session)
    for perp in HYPERLIQUID_PERPS:
        existing = session.exec(
            select(Symbol).where(
                Symbol.symbol == perp["symbol"],
                Symbol.exchange == "hyperliquid",
            )
        ).first()
        if existing:
            continue
        session.add(
            Symbol(
                symbol_id=next_id,
                symbol=perp["symbol"],
                display_name=perp["display_name"],
                exchange="hyperliquid",
                symbol_type="perp",
                is_active=True,
            )
        )
        next_id += 1


def _seed_yahoo(session: Session) -> None:
    next_id = _next_symbol_id(session)
    for asset in YAHOO_POPULAR:
        existing = session.exec(
            select(Symbol).where(
                Symbol.symbol == asset["symbol"],
                Symbol.exchange == "yahoo",
            )
        ).first()
        if existing:
            continue
        session.add(
            Symbol(
                symbol_id=next_id,
                symbol=asset["symbol"],
                display_name=asset["display_name"],
                exchange="yahoo",
                symbol_type=asset["type"],
                is_active=True,
            )
        )
        next_id += 1


if __name__ == "__main__":
    seed()
    print("Database seeded successfully")
