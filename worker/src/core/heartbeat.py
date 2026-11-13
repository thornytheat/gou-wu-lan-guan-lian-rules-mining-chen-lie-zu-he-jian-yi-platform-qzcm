"""Redis 心跳：worker 每 30s 写一次，healthcheck 与前端状态条读取。"""
from __future__ import annotations

import socket
import time

import redis

from src.config.settings import settings

HEARTBEAT_KEY = "basketrule:worker:heartbeat"


def beat() -> float:
    now = time.time()
    try:
        client = redis.Redis.from_url(settings.redis_url, decode_responses=True)
        client.set(HEARTBEAT_KEY, f"{now:.3f}", ex=180)
        client.set("basketrule:worker:host", socket.gethostname(), ex=180)
    except Exception:  # noqa: BLE001 - 心跳失败不允许打断任务
        pass
    return now
