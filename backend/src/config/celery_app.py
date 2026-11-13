"""Celery 入口（backend 只投递任务，消费在 worker 容器）。"""
from __future__ import annotations

from celery import Celery

from src.config.settings import settings

celery_app = Celery(
    "basketrule",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Shanghai",
    enable_utc=False,
    task_track_started=True,
    result_expires=3600,
    broker_connection_retry_on_startup=True,
)

# 任务名 -> worker 侧真实实现（跨容器共享任务名）
TASK_RUN_MINING = "basketrule.run_mining"
TASK_HEARTBEAT = "basketrule.heartbeat"
