"""挖掘任务：调用 backend 的算法服务（同一份代码，跨容器共享任务名）。"""
from __future__ import annotations

from worker_src.config.celery_app import celery_app
from worker_src.core.heartbeat import beat
from src.utils.logger import get_logger

logger = get_logger("basketrule.worker.mining")


@celery_app.task(name="basketrule.run_mining", bind=True, max_retries=1, default_retry_delay=5)
def run_mining(self, run_id: str) -> dict:  # noqa: ANN001
    beat()
    from src.services.mining_service import execute_run

    logger.info("worker picked mining run %s", run_id)
    execute_run(run_id)
    beat()
    return {"run_id": run_id, "status": "done"}
