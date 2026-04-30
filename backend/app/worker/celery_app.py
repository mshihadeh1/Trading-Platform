"""Compatibility wrapper for the shared Celery app."""

from app.celery import celery_app

__all__ = ["celery_app"]
