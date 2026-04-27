"""Seed the database with default watchlist symbols."""

from sqlmodel import Session, select
from app.database import engine, init_db
from app.models.symbol import Symbol
from app.services.hyperliquid import HYPERLIQUID_PERPS
from app.services.yahoo_finance import YAHOO_POPULAR


def seed():
    init_db()

    with Session(engine) as session:
        # Seed Hyperliquid symbols
        for p in HYPERLIQUID_PERPS:
            existing = session.exec(
                select(Symbol).where(Symbol.symbol == p["symbol"], Symbol.exchange == "hyperliquid")
            ).first()
            if not existing:
                session.add(Symbol(
                    symbol=p["symbol"],
                    display_name=p["display_name"],
                    exchange="hyperliquid",
                    asset_type="crypto",
                    is_active=True,
                ))

        # Seed Yahoo Finance symbols
        for y in YAHOO_POPULAR:
            existing = session.exec(
                select(Symbol).where(Symbol.symbol == y["symbol"], Symbol.exchange == "yahoo_finance")
            ).first()
            if not existing:
                session.add(Symbol(
                    symbol=y["symbol"],
                    display_name=y["display_name"],
                    exchange="yahoo_finance",
                    asset_type=y["type"],
                    is_active=True,
                ))

        session.commit()
        print("✓ Database seeded successfully")


if __name__ == "__main__":
    seed()
