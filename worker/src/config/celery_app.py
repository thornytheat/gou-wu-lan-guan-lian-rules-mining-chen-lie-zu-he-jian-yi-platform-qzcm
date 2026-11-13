"""worker 侧 Celery 入口：任务名必须与 backend src/config/celery_app.py 一致。"""
from __future__ import annotations

from celery import Celery

from src.config.settings import settings

celery_app = Celery(
    "basketrule",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["worker_src.tasks.mining_task", "worker_src.tasks.heartbeat_task"],
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
    worker_max_tasks_per_child=60,
)

celery_app.conf.beat_schedule = {
    "basketrule-heartbeat": {
        "task": "basketrule.heartbeat",
        "schedule": 30.0,
    }
}
