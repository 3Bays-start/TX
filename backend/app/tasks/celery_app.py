"""Celery 应用。CELERY_ENABLED=false 时使用进程内后台调度（见 scheduler）。撮合仅由管理后台触发。"""

from __future__ import annotations

from celery import Celery

from app.config import settings

celery_app = Celery(
    "lx_platform",
    broker=settings.broker_url,
    backend=settings.CELERY_RESULT_BACKEND or settings.broker_url,
    include=["app.tasks.matching_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_ignore_result=False,
    beat_schedule={},
)
