"""Time helpers for the trading platform.

The application stores timestamps as naive UTC datetimes in SQLite. Python 3.12
warns on datetime.utcnow(), so use timezone-aware UTC internally and strip the
timezone at the boundary to preserve the existing DB/API convention.
"""

from datetime import UTC, datetime


def utc_now() -> datetime:
    """Return a naive UTC datetime compatible with existing DB columns."""
    return datetime.now(UTC).replace(tzinfo=None)
