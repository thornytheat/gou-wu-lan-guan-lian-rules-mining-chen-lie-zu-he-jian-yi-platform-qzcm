"""导出路由占位：CSV 导出挂在 rules / planogram 路由上（保持 /api 前缀一致）。"""
from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["export"])
