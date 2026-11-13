"""路由汇总。"""
from __future__ import annotations

from fastapi import APIRouter

from src.routes import audit, auth, baskets, export, health, ingest, mining, planogram, rules

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(baskets.router)
api_router.include_router(ingest.router)
api_router.include_router(mining.router)
api_router.include_router(rules.router)
api_router.include_router(planogram.router)
api_router.include_router(export.router)
api_router.include_router(audit.router)
