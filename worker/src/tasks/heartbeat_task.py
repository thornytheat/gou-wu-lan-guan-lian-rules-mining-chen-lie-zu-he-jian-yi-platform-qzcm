"""周期心跳任务（beat 调度）。"""
from __future__ import annotations

from worker_src.config.celery_app import celery_app
from worker_src.core.heartbeat import beat


@celery_app.task(name="basketrule.heartbeat", ignore_result=True)
def heartbeat() -> str:
    return f"beat {beat():.0f}"
