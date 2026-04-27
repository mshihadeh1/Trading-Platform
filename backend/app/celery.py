"""Celery configuration for the trading platform."""

import os

from celery import Celery

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
celery_app.conf.beat_schedule = {
    "fetch-historical-data": {
        "task": "worker.tasks.fetch_historical_data",
        "schedule": 300,  # every 5 minutes
    },
    "analyze-all-signals": {
        "task": "worker.tasks.analyze_all_signals",
        "schedule": 14400,  # every 4 hours
    },
    "check-paper-trades": {
        "task": "worker.tasks.check_paper_trades",
        "schedule": 30,  # every 30 seconds
    },
}

celery_app.conf.timezone = "UTC"
celery_app.conf.enable_utc = True
