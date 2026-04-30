"""Celery configuration for the trading platform."""

import os

from celery import Celery

from app.config import settings

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "trading_platform",
    broker=REDIS_URL,
    backend=REDIS_URL,
)

celery_app.config_from_object({
    "broker_url": REDIS_URL,
    "result_backend": REDIS_URL,
    "imports": [
        "app.worker.tasks",
    ],
    "task_serializer": "json",
    "result_serializer": "json",
    "accept_content": ["json"],
    "task_track_started": True,
    "task_acks_late": True,
})

# Scheduled tasks
_daily_brief_interval = settings.daily_brief_interval_hours * 3600 if settings.daily_brief_enabled else None

celery_app.conf.beat_schedule = {
    "collect-candles": {
        "task": "app.worker.tasks.collect_candles",
        "schedule": 300,
    },
    "analyze-watchlist": {
        "task": "app.worker.tasks.analyze_watchlist",
        "schedule": 14400,
    },
    "check-sl-tp": {
        "task": "app.worker.tasks.check_sl_tp",
        "schedule": 30,
    },
}

if _daily_brief_interval is not None:
    celery_app.conf.beat_schedule["generate-daily-brief"] = {
        "task": "app.worker.tasks.generate_daily_brief",
        "schedule": _daily_brief_interval,
    }

celery_app.conf.timezone = "UTC"
celery_app.conf.enable_utc = True
